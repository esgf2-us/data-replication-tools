from datetime import datetime
from sqlalchemy import Column, ForeignKey, Boolean, Integer, BigInteger, Numeric, String, DateTime
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship


DBSession = scoped_session(sessionmaker())
Base = declarative_base()


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True)
    source = Column(String)
    destination = Column(String)
    uuid = Column(String)
    code = Column(String)
    description = Column(String)
    is_error = Column(Boolean)
    details = Column(String)
    time = Column(DateTime)
    bytes_transferred = Column(BigInteger)
    mbps = Column(Numeric(10, 2))
    duration = Column(Numeric(10, 2))

    def __repr__(self):
        return f"Event(id={self.id}, uuid={self.uuid}, code={self.code}, description={self.description})"


class EventSummary(Base):
    __tablename__ = "event_summary"

    id = Column(Integer, primary_key=True)
    uuid = Column(String)
    events = Column(Integer)
    downloaded = Column(Boolean)

    def __repr__(self):
        return f"EventSummary(id={self.id}, uuid={self.uuid}, events={self.events}, downloaded={self.downloaded})"


class Transfer(Base):
    __tablename__ = "transfer"

    id = Column(Integer, primary_key=True)
    dataset = Column(String)
    source = Column(String)
    destination = Column(String)
    uuid = Column(String)
    requested = Column(DateTime)
    completed = Column(DateTime)
    status = Column(String)
    directories = Column(BigInteger)
    files = Column(BigInteger)
    files_transferred = Column(BigInteger)
    rate = Column(BigInteger)
    faults = Column(BigInteger)
    bytes_transferred = Column(BigInteger)

    __table_args__ = (UniqueConstraint('dataset', 'destination', name='dataset_destination'),)

    def __repr__(self):
        return "Transfer(id={}, uuid={}, dataset={}, from={}, to={}, status={}, rate={}, faults={})".format(
            self.id, self.uuid, self.dataset, self.source, self.destination, self.status, self.rate, self.faults)
