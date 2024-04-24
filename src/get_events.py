import logging
import os
import json
import time
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
    session.commit()


def find_transfer(transfer_client, session):
    transfer = session.query(Transfer).\
        outerjoin(EventSummary, Transfer.uuid==EventSummary.uuid).\
        filter(Transfer.status=='SUCCEEDED').\
        filter(EventSummary.uuid==None).\
        order_by(Transfer.id).first()
    print("TRANSFER", transfer)
    if transfer:
        get_events(transfer_client, session, transfer.uuid, transfer.source, transfer.destination)
        return True
    return False


def main():
    engine = create_engine(settings.database.get("url"))
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)

    transfer_client = get_transfer_client()

    session = DBSession()
    while find_transfer(transfer_client, session):
        time.sleep(5)
    session.close()


if __name__ == "__main__":
    main()
