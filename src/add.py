import sys
from pathlib import Path
from sqlalchemy import create_engine, exists
from models import DBSession, Base, Transfer
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

def main():
    engine = create_engine(settings.database.get("url"))
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    session = DBSession()

    paths = []
    for line in sys.stdin:
        paths.append(line.rstrip())
    paths.sort(key=lambda x: x.lower())

    for destination in ['ALCF', 'OLCF']:
        for path in paths:
            transfer = Transfer(dataset=path, destination=destination)
            session.add(transfer)
            print(path)

    session.commit()
    session.close()


if __name__ == "__main__":
    main()
