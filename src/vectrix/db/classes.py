from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
import pytz
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Tables:
    def __init__(self, engine):
        Base.metadata.create_all(engine)


    class Prompt(Base):
        __tablename__ = 'prompts'

        id = Column(Integer, primary_key=True)
        name = Column(String(255), nullable=False)
        prompt = Column(Text, nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))


    class Project(Base):
        __tablename__ = 'projects'
        id = Column(Integer, primary_key=True)
        name = Column(String(255), nullable=False)
        description = Column(Text, nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    class APIKeys(Base):
        __tablename__ = 'api_keys'
        id = Column(Integer, primary_key=True)
        name = Column(String(255), nullable=False)
        key = Column(String(255), nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    class LinksToConfirm(Base):
        __tablename__ = 'links_to_index'
        id = Column(Integer, primary_key=True)
        url = Column(String(255), nullable=False)
        base_url = Column(String(255), nullable=False)
        project_name = Column(String(255), nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    class ScrapeStatus(Base):
        __tablename__ = 'scrape_status'
        id = Column(Integer, primary_key=True)
        base_url = Column(String(255), nullable=True)
        status = Column(String(255), nullable=False)
        project_name = Column(String(255), nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))