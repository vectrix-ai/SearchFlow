from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Float, ARRAY
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
        name = Column(String(255), primary_key=True)
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

    class IndexedLinks(Base):
        __tablename__ = 'indexed_links'
        id = Column(Integer, primary_key=True)
        url = Column(String(255), nullable=False)
        base_url = Column(String(255), nullable=False)
        status = Column(String(255), nullable=False)
        project_name = Column(String(255), nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))
        __table_args__ = (
            UniqueConstraint('url', 'project_name', name='uq_url_project'),
        )

    class Documents(Base):
        __tablename__ = 'document_metadata'
        id = Column(Integer, primary_key=True, autoincrement=True)
        title = Column(String(255), nullable=False)
        author = Column(String(255))
        file_type = Column(String(50))
        word_count = Column(Integer)
        language = Column(String(50))
        source = Column(String(255))
        content_type = Column(String(100))
        tags = Column(ARRAY(String))  # Store as an array of strings
        summary = Column(Text)
        url = Column(String(255))
        project_name = Column(String(255), ForeignKey('projects.name'))
        indexing_status = Column(String(50))
        filename = Column(String(255))
        priority = Column(Integer)
        read_time = Column(Float)  # in minutes
        creation_date = Column(DateTime(timezone=True))
        last_modified_date = Column(DateTime(timezone=True))
        upload_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        
        __table_args__ = (
            UniqueConstraint('url', 'project_name', name='uq_doc_url_project'),
        )