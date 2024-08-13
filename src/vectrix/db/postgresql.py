from datetime import datetime
from typing import List
from vectrix import logger 
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from langchain_core.documents import Document
import pytz

Base = declarative_base()

class DB:
    """
    A class for managing prompts in a database.

    This class provides methods to add, update, remove, and retrieve prompts
    stored in a SQL database using SQLAlchemy ORM.

    Attributes:
        engine: SQLAlchemy database engine
        Session: SQLAlchemy session factory

    Methods:s
        add_prompt: Add a new prompt to the database
        update_prompt: Update an existing prompt in the database
        remove_prompt: Remove a prompt from the database
        get_all_prompts: Retrieve all prompts from the database
    """
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logger.setup_logger()
        
        # Create the table if it doesn't exist
        Base.metadata.create_all(self.engine)

    class Prompt(Base):
        __tablename__ = 'prompts'

        id = Column(Integer, primary_key=True)
        name = Column(String(255), nullable=False)
        prompt = Column(Text, nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

    class WebDocument(Base):
        __tablename__ = 'documents'
        id = Column(Integer, primary_key=True)
        url = Column(String(255), nullable=False)
        page_hash = Column(String(255), nullable=False)
        domain_name = Column(String(255), nullable=False)
        storage_location = Column(String(255), nullable=False)
        content = Column(JSON(none_as_null=True), nullable=False)  # <--- Made this a JSON column
        indexing_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))


    def add_document(self, url : str, page_hash :str , domain_name :str , storage_location:str, content: dict):
        """
        Add a new document (webpage) to the database.

        This method creates a new Document object with the provided information
        and adds it to the database.

        Args:
            url (str): The URL of the webpage.
            page_hash (str): A hash of the webpage content.
            domain_name (str): The domain name of the webpage.
            storage_location (str): The location where the webpage content is stored.

        Returns:
            int: The ID of the newly added document in the database.

        Raises:
            Exception: If there's an error during the database operation,
                    the transaction is rolled back and the error is logged.

        Note:
            This method uses a new database session for the operation and
            commits the transaction if successful. In case of an error,
            it performs a rollback.
        """
        session = self.Session()
        try:
            new_webpage = self.WebDocument(url=url, page_hash=page_hash, domain_name=domain_name, storage_location=storage_location, content=content)
            session.add(new_webpage)
            session.commit()
            self.logger.info(f"Added webpage: {url}")
            return new_webpage.id
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding webpage: {e}")
            session.close()

    def list_documents(self, domain_name):
        """
        List all indexed pages for a given domain name.
        """
        session = self.Session()
        self.logger.info("Listing all pages for domain: %s", domain_name)
        try:
            pages = session.query(self.WebDocument).filter_by(domain_name=domain_name).all()
            session.close()
            return [page.url for page in pages]
        except Exception as e:
            session.close()
            self.logger.error(f"Error listing pages: {e}")

    def get_documents(self, domain_name : str) -> List[Document]:
        '''
        Get all documents from a given domain name
        This function will return the documents as a list of Langchain Docs
        '''
        session = self.Session()
        self.logger.info(f"Getting all documents for domain: {domain_name}")
        try:
            documents = session.query(self.WebDocument).filter_by(domain_name=domain_name).all()
            session.close()
            return [Document(page_content=doc.content['raw_text'], 
                             metadata={
                                 "title": doc.content['title'],
                                 "url": doc.url,
                                 "language" : doc.content['language'],
                                 "source_type" : "webpage",
                                 "source_format" : "html"})for doc in documents]
        except  Exception as e:
            session.close()
            self.logger.error(f"Error getting documents: {e}")


    def remove_documents(self, id = None, domain_name = None):
        """
        Remove documents based on ID or domain name.
        """
        session = self.Session()
        try:
            if id:
                session.query(self.Document).filter_by(id=id).delete()
                session.close()
            elif domain_name:
                session.query(self.Document).filter_by(domain_name=domain_name).delete()
                session.close()

            session.commit()
            print("Removed documents successfully.")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error removing documents: {e}")

    def add_prompt(self, name, prompt_text):
        """
        Add a new prompt to the database.

        Args:
            name (str): The name of the prompt.
            prompt_text (str): The text content of the prompt.

        Returns:
            int: The ID of the newly added prompt if successful, None otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Adding new prompt: {name}")
        try:
            new_prompt = self.Prompt(name=name, prompt=prompt_text)
            session.add(new_prompt)
            session.commit()
            print(f"Added new prompt: {name}")
            return new_prompt.id
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding prompt: {e}")
        finally:
            session.close()

    def update_prompt(self, prompt_id, name=None, prompt_text=None):
        """
        Update an existing prompt in the database.

        Args:
            prompt_id (int): The ID of the prompt to update.
            name (str, optional): The new name for the prompt. If None, the name remains unchanged.
            prompt_text (str, optional): The new text content for the prompt. If None, the text remains unchanged.

        Returns:
            bool: True if the prompt was successfully updated, False otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Updating prompt with ID: {prompt_id}")
        try:
            prompt = session.query(self.Prompt).filter_by(id=prompt_id).first()
            if prompt:
                if name:
                    prompt.name = name
                if prompt_text:
                    prompt.prompt = prompt_text
                prompt.update_date = datetime.now(pytz.UTC)
                session.commit()
                print(f"Updated prompt with ID: {prompt_id}")
                return True
            else:
                print(f"No prompt found with ID: {prompt_id}")
                return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating prompt: {e}")
            return False
        finally:
            session.close()



    def get_prompt_by_name(self, name):
        """
        Get a prompt from the database by its name.
        """
        session = self.Session()
        self.logger.info(f"Retrieving prompt by name: {name}")
        try:
            prompt = session.query(self.Prompt).filter_by(name=name).first()
            if prompt:
                return prompt.prompt
            else:
                self.logger.error(f"No prompt found with name: {name}")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving prompt by name: {e}")  
        finally:
            session.close()

    def remove_prompt(self, prompt_id):
        """
        Remove a prompt from the database.

        Args:
            prompt_id (int): The ID of the prompt to remove.

        Returns:
            bool: True if the prompt was successfully removed, False otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Removing prompt with ID: {prompt_id}")
        try:
            prompt = session.query(self.Prompt).filter_by(id=prompt_id).first()
            if prompt:
                session.delete(prompt)
                session.commit()
                print(f"Removed prompt with ID: {prompt_id}")
                return True
            else:
                print(f"No prompt found with ID: {prompt_id}")
                return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error removing prompt: {e}")
            return False
        finally:
            session.close()

    def get_all_prompts(self):
        """
        Retrieve all prompts from the database.

        Returns:
            list: A list of all Prompt objects stored in the database.

        Note:
            This method creates a new session, queries all prompts, and closes the session
            after the query is executed, regardless of whether an exception occurs.
        """
        session = self.Session()
        self.logger.info("Retrieving all prompts")
        try:
            prompts = session.query(self.Prompt).all()
            return prompts
        finally:
            session.close()