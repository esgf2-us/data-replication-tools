import traceback
import logging
import os
import json
from datetime import datetime, timedelta
from globus_sdk import TransferClient, TransferData
from fair_research_login.client import NativeClient
from fair_research_login.token_storage import MultiClientTokenStorage
from sqlalchemy import create_engine, and_, or_, not_
from sqlalchemy.orm import aliased
from sqlalchemy.sql import expression
from models import DBSession, Base, Event, EventSummary, Transfer
import local_settings as settings

"""
local_settings.py module includes credentials to the database and Globus.
It has the following format:

database = {
    "url": "postgresql://<username>:<password>@localhost:5432/<database>"
}

globus = {
    "client_id": <client_id>,
    "redirect_uri": "https://auth.globus.org/v2/web/auth-code",
    "scopes": "openid urn:globus:auth:scope:transfer.api.globus.org:all"
}
"""


logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "WARNING"),
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
    filename=os.environ.get("LOGFILE", "../log/replication.log")
)
logger = logging.getLogger(__name__)

endpoints = {
    "ALCF": "8896f38e-68d1-4708-bce4-b1b3a3405809",
    "LLNL": "dd1ee76f-6d04-11e5-ba46-22000b92c6ec",
    "OLCF": "ef1a9560-7ca1-11e5-992c-22000b96db58",
}

path_prefix = {
    "ALCF": "/",
    "LLNL": "/",
    "OLCF": "/gpfs/alpine/cli137/proj-shared/ESGF/esg_dataroot",
}


def get_transfer_client():
    filename = os.path.expanduser("~/.esgf-replication-native-client.cfg")
    token_storage = MultiClientTokenStorage(filename=filename)
    native_client = NativeClient(
        token_storage=token_storage,
        client_id=settings.globus.get("client_id"),
        app_name="ESGF Data Replication Tool",
        default_scopes=settings.globus.get("scopes")
    )
    native_client.login(no_local_server=True, refresh_tokens=True)
    transfer_authorizer = native_client.get_authorizers().get("transfer.api.globus.org")
    return TransferClient(authorizer=transfer_authorizer)


def get_error_events(tc, task_id, limit):
    events = tc.task_event_list(task_id, limit=limit, query_params={"filter":"is_error:1"})
    return events


def is_paused(tc, task_id):
    events = get_error_events(tc, task_id, 1)
    for event in events:
        if event.get("code") == "PAUSED":
            return True
        break
    return False


def get_events(transfer_client, session, uuid, source, destination):
    limit = 1000
    offset = 0
    total = None
    while True:
        events = transfer_client.task_event_list(uuid, limit=limit, offset=offset)
        total = events.get("total")
        for event in events:
            description = event.get("description")
            details=event.get("details")
            event = Event(
                uuid=uuid,
                source=source,
                destination=destination,
                code=event.get("code"),
                description=description,
                is_error=event.get("is_error"),
                details=details,
                time=event.get("time")
            )
            if description == "progress":
                details_dict = json.loads(details)
                event.bytes_transferred = details_dict.get("bytes_transferred")
                event.mbps = details_dict.get("mbps")
                event.duration = details_dict.get("duration")
            session.add(event)
        if offset + limit >= total:
            break
        offset += limit
    event_summary = EventSummary(
        uuid=uuid,
        events=total,
        downloaded=True)
    print(event_summary)
    session.add(event_summary)


def transfer(transfer_client, session, source, destination, update_only=False):
    print(f"{source} -> {destination}")
    # check active transfers
    if source == "LLNL" and destination == "ALCF":
        order_expr = Transfer.dataset
    elif source == "LLNL" and destination == "OLCF":
        order_expr = Transfer.dataset.desc()
    elif source == "ALCF" and destination == "OLCF":
        order_expr = Transfer.dataset
    else:
        order_expr = Transfer.dataset.desc()

    # get all active transfers (ACTIVE, PAUSED, etc.) from the database
    transfers = session.query(Transfer).\
        filter(Transfer.source==source).\
        filter(Transfer.destination==destination).\
        filter(Transfer.uuid!='').\
        filter(or_(Transfer.status==None,
                   and_(Transfer.status!='SUCCEEDED',
                        Transfer.status!='FAILED'))).\
        order_by(Transfer.dataset).all()

    # update the dataset with the latest info from Globus
    succeeded = 0
    if transfers:
        print("ACTIVE transfers:")
    for transfer in transfers:
        # update active transfers
        paused = is_paused(transfer_client, transfer.uuid)
        t = transfer_client.get_task(transfer.uuid)
        transfer.requested = t.get("request_time")
        transfer.completed = t.get("completion_time")
        transfer.status = "PAUSED" if paused else t.get("status")
        transfer.directories = t.get("directories")
        transfer.files = t.get("files")
        transfer.files_transferred = t.get("files_transferred")
        transfer.rate = t.get("effective_bytes_per_second")
        transfer.faults = t.get("faults")
        transfer.bytes_transferred = t.get("bytes_transferred")
        if transfer.status == 'SUCCEEDED':
            succeeded += 1
            get_events(transfer_client, session, transfer.uuid, source, destination)
        print("ACTIVE", transfer)
        session.commit()

    for transfer in transfers:
        if transfer.status == "PAUSED":
            return True

    if update_only:
        return

    # if the number of active transfer is less than 1, submit a new transfer
    if len(transfers) - succeeded < 3:
        # transfer from the original source (LLNL)
        if source == "LLNL":
            print("LLNL source")
            datasets = session.query(Transfer.dataset).\
                filter(Transfer.destination==destination,
                    or_(Transfer.uuid==None,
                    Transfer.status=="FAILED")).\
                order_by(order_expr).first()
        else:
            # exchange transfer (from ALCF or OLCF)
            t = aliased(Transfer)
            if source=="OLCF" and destination=="ALCF":
                datasets = session.query(Transfer.dataset).\
                    join(t, and_(
                        Transfer.destination==source,
                        Transfer.status=="SUCCEEDED",
                        t.destination==destination,
                        or_(t.uuid==None,
                             t.status=="FAILED"),
                        Transfer.dataset==t.dataset)).\
                    order_by(order_expr).first()
            else:
                datasets = session.query(Transfer.dataset).\
                    join(t, and_(
                        Transfer.destination==source,
                        Transfer.status=="SUCCEEDED",
                        t.destination==destination,
                        or_(t.uuid==None,
                             t.status=="FAILED"),
                        Transfer.dataset==t.dataset)).\
                    order_by(order_expr).first()
        if datasets:
            dataset = datasets[0]
        else:
            return
        print("NEW", dataset)

        transfer = session.query(Transfer).\
            filter(Transfer.destination==destination).\
            filter(Transfer.dataset==dataset).\
            first()
        print(transfer)

        source_uuid = endpoints.get(source)
        destination_uuid = endpoints.get(destination)

        filter_rule = {
            "DATA_TYPE": "filter_rule",
            "method": "exclude",
            "type": "file",
            "name": ".*"
        }

        td = TransferData(transfer_client,
            source_uuid,
            destination_uuid,
            sync_level="checksum",
            verify_checksum=True,
            preserve_timestamp=True,
            fail_on_quota_errors=True,
            additional_fields={"filter_rules": [filter_rule]}
        )
        #    sync_level="checksum",
        src_path = os.path.join(path_prefix.get(source), transfer.dataset.strip("/"))
        dst_path = os.path.join(path_prefix.get(destination), transfer.dataset.strip("/"))
        print(src_path, dst_path)
        td.add_item(src_path, dst_path, recursive=True)

        try:
            task = transfer_client.submit_transfer(td)
            transfer.uuid = task.get("task_id")
            transfer.source = source
            transfer.status = task.get("status")
            transfer.requested = task.get("request_time")
            session.commit()
        except Exception as e:
            traceback.print_exc()
            logger.error(f"LLNL:{transfer.dataset}->{destination} - exception: {e}")


def main():
    engine = create_engine(settings.database.get("url"))
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)

    transfer_client = get_transfer_client()

    for uuid in endpoints.values():
        r = transfer_client.endpoint_autoactivate(uuid)
        if r["code"] == "AutoActivationFailed":
            print("Autoactivation error", uuid, r["message"])
            logger.error("Endpoint autoactivation failed for endpoint {}: {}".format(uuid, r["message"]))

    session = DBSession()
    if transfer(transfer_client, session, "LLNL", "ALCF"):
        transfer(transfer_client, session, "LLNL", "OLCF")
    else:
        transfer(transfer_client, session, "LLNL", "OLCF", update_only=True)
    transfer(transfer_client, session, "ALCF", "OLCF")
    transfer(transfer_client, session, "OLCF", "ALCF")
    session.close()


if __name__ == "__main__":
    main()
