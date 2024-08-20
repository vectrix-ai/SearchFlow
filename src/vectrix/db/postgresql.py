import os
import uuid
from datetime import datetime
from typing import Annotated, Optional, List, Tuple, Callable
from vectrix import logger
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from langchain_core.documents import Document
from langchain_cohere import CohereEmbeddings
from langchain_postgres.vectorstores import PGVector

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
    def __init__(self):
        self.logger = logger.setup_logger()
        self.db_name = os.getenv('DB_NAME')
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT')
        self.db_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        try:
            self.engine = create_engine(self.db_url)
        except:
            self.logger.error('Unable to connect to database, please check the connection string: %s', self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        # Create the table if it doesn't exist
        Base.metadata.create_all(self.engine)
        vectorstore = PGVector(CohereEmbeddings(model="embed-multilingual-v3.0"), connection=self.engine)
        vectorstore.create_tables_if_not_exists()

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

    def list_projects(self):
        """
        List all projects in the database.
        """

        session = self.Session()
        try:
            projects = session.query(DB.Project).all()
            session.close()
            return [project.name for project in projects]
        except Exception as e:
            session.close()


    async def asimilarity_search(self, question: str, project_name: str):

        db_url = f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        async_engine = create_async_engine(db_url)

        async_vectorstore = PGVector(
            embeddings=CohereEmbeddings(model="embed-multilingual-v3.0"),
            collection_name=project_name,
            connection=async_engine,
            use_jsonb=True,
            create_extension=False,
            async_mode=True,
        )

        result = await async_vectorstore.asimilarity_search_with_relevance_scores(question, k=3)

        # Add the score to the result metadata

        return result
    
    def list_scraped_urls(self) -> List[str]:
        """
        List all scraped URLs in the database.
        """
        session = self.Session()
        query = text("""
            SELECT DISTINCT jsonb_extract_path_text(cmetadata, 'url') as url
            FROM langchain_pg_embedding
            WHERE jsonb_extract_path_text(cmetadata, 'url') IS NOT NULL
        """)
        result = session.execute(query)
        unique_urls = [row.url for row in result]
        session.close()
        return unique_urls
    
    def get_collection_metdata(self, project_name: str):
        '''
        Get the metadata of a collection
        '''
        query = text(f"""
            select
            langchain_pg_embedding.cmetadata as metadata
            from
            langchain_pg_embedding
            join langchain_pg_collection on langchain_pg_embedding.collection_id = langchain_pg_collection.uuid
            where
            langchain_pg_collection.name = '{project_name}'
        """)
        session = self.Session()
        result = session.execute(query)
        metadata = [row.metadata for row in result]
        session.close()
        return metadata

    def add_documents(self, documents: List[Document], project_name: str):
        '''
        Calculate Vectors for a set of documents and upload them to the database
        '''

        vectorstore = PGVector(
            embeddings=CohereEmbeddings(),
            collection_name=project_name,
            connection=self.engine,
            use_jsonb=True,
        )

        ids = [doc.metadata["uuid"] for doc in documents]
        result = vectorstore.add_documents(documents, ids=ids)

    def similarity_search(self, project_name: str, query: str, top_k: int = 3):
        '''
        Search for similar documents in a project
        '''
        vectorstore = PGVector(
            embeddings=self.embeddings,
            collection_name=project_name,
            connection=self.engine,
            use_jsonb=True,
        )

        result = vectorstore.similarity_search(query, top_k=top_k)
        return result
 
    def create_project(self, name, description):
        """
        Add a new project to the database.

        Args:
            name (str): The name of the project.
            description (str): The description of the project.

        Returns:
            int: The ID of the newly added project if successful, None otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Adding new project: {name}")
        try:
            existing_project = session.query(self.Project).filter_by(name=name).first()
            if existing_project:
                self.logger.error(f"Project with name '{name}' already exists. Skipping creation.")
                return existing_project.id

            new_project = self.Project(name=name, description=description)
            session.add(new_project)
            session.commit()
            vectorstore = PGVector(
                embeddings=self.embeddings,
                collection_name=name,
                connection=self.engine,
                use_jsonb=True,
            )
            vectorstore.create_collection()
            self.logger.info(f"Added new project: {name}")
            return new_project.id
        
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding project: {e}")
        finally:
            session.close()

    def remove_project(self, project_name):
        """
        Remove a project from the database.

        Args:
            project_name (str): The name of the project to remove.

        Returns:
            bool: True if the project was successfully removed, False otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Removing project: {project_name}")
        try:
            project = session.query(self.Project).filter_by(name=project_name).first()
            if project:
                session.delete(project)
                session.commit()
                vectorstore = PGVector(
                    embeddings=self.embeddings,
                    collection_name=project_name,
                    connection=self.engine,
                    use_jsonb=True,
                )
                vectorstore.delete_collection()
                self.logger.info(f"Removed project: {project_name}")
                return True
            else:
                self.logger.error(f"No project found with name: {project_name}")
                return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error removing project: {e}")
            return False
        finally:
            session.close()
 
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
    
    def add_api_key(self, name, key):
        """
        Add a new API key to the database.

        Args:
            name (str): The name of the API key.
            key (str): The API key.

        Returns:
            int: The ID of the newly added API key if successful, None otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Adding new API key: {name}")
        try:
            new_key = self.APIKeys(name=name, key=key)
            session.add(new_key)
            session.commit()
            print(f"Added new API key: {name}")
            return new_key.id
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding API key: {e}")
        finally:
            session.close()

    def remove_api_key(self, name: str):
        """
        Remove an API key from the database.

        Args:
            name (str): The name of the API key to remove.

        Returns:
            bool: True if the API key was successfully removed, False otherwise.

        Raises:
            Exception: If there's an error during the database operation.
        """
        session = self.Session()
        self.logger.info(f"Removing API key: {name}")
        try:
            key = session.query(self.APIKeys).filter_by(name=name).first()
            if key:
                session.delete(key)
                session.commit()
                print(f"Removed API key: {name}")
                return True
            else:
                print(f"No API key found with name: {name}")
                return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error removing API key: {e}")
            return False
        finally:
            session.close()


    def get_api_key_by_name(self, name):
        """
        Get an API key from the database by its name.
        """
        session = self.Session()
        self.logger.info(f"Retrieving API key by name: {name}")
        try:
            key = session.query(self.APIKeys).filter_by(name=name).first()
            if key:
                return key.key
            else:
                self.logger.error(f"No API key found with name: {name}")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving API key by name: {e}")  
        finally:
            session.close()

    def list_api_keys(self) -> List[dict]:
        """
        List all API keys in the database. As a list of dicts
        """
        session = self.Session()
        self.logger.info("Retrieving all API keys")
        try:
            keys = session.query(self.APIKeys).all()
            return [{"name": key.name, "key": key.key} for key in keys]
        finally:
            session.close()