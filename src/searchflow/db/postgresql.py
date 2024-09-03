import os
import uuid
from datetime import datetime
from typing import List, Annotated
from searchflow import logger
from sqlalchemy import create_engine, text, func
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from supabase import create_client, Client
from langchain_core.documents import Document
from langchain_cohere import CohereEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from searchflow.db.tables import Tables
import pytz


def chunk_content(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 0) -> List[Document]:
    """
    Chunk the content of the pages into smaller chunks. Will also add UUIDs to the chunks.

    Args:
        chunk_size (int): The maximum size of each chunk in characters. Defaults to 1000.

    Returns:
        list: A list of chunks containing the content of the pages.
    """
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    model_name="gpt-4",
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    )
    
    metadatas = [doc.metadata for doc in documents]
    content = [' '.join(doc.page_content.split()) for doc in documents]

    chunks = text_splitter.create_documents(content, metadatas=metadatas)

    for chunk in chunks:
        chunk.metadata['uuid'] = str(uuid.uuid4())
        
    return chunks


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
        self.logger = logger.setup_logger(name="DB", level="WARNING")
        self.embeddings = CohereEmbeddings(model="embed-multilingual-v3.0")
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
        self.tables = Tables(self.engine)
        self.supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
        
        vectorstore = PGVector(self.embeddings, connection=self.engine)
        vectorstore.create_tables_if_not_exists()


    def list_projects(self):
        """
        List all projects in the database.
        """

        session = self.Session()
        try:
            projects = session.query(self.tables.Project).all()
            session.close()
            return [project.name for project in projects]
        except Exception as e:
            session.close()


    async def asimilarity_search(self, question: str, project_name: str):

        db_url = f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        async_engine = create_async_engine(db_url)

        async_vectorstore = PGVector(
            embeddings=self.embeddings,
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
        List all vectorized documents in the database.
        - FUNCTION NAME SHOULD BE UPDATED TO LIST_INDEXED_DATA
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
    
    def remove_by_url(self, project_name: str, url: str) -> None:
        '''
        Remove all documents that have the specified URL in their metadata

        args:
            project_name (str): The name of the project
            url (str): The URL to search for

        returns:
            None
        '''
        query = text(f"""
            DELETE FROM langchain_pg_embedding
            WHERE cmetadata->>'url' = '{url}'
            AND collection_id = (
                SELECT uuid
                FROM langchain_pg_collection
                WHERE name = '{project_name}'
            )
        """)
        session = self.Session()
        session.execute(query)
        session.commit()
        session.close()
    
    def get_collection_metdata(self, project_name: str):
        '''
        Get the metadata of a collection
        '''
        query = text(f"""
            SELECT
                langchain_pg_embedding.cmetadata->>'title' AS title,
                langchain_pg_embedding.cmetadata->>'source' AS source,
                langchain_pg_embedding.cmetadata->>'file_type' AS file_type,
                langchain_pg_embedding.cmetadata->>'url' AS url
            FROM
                langchain_pg_embedding
            JOIN
                langchain_pg_collection ON langchain_pg_embedding.collection_id = langchain_pg_collection.uuid
            WHERE
                langchain_pg_collection.name = '{project_name}'
        """)
        session = self.Session()
        result = session.execute(query)
        metadata = [row for row in result]
        session.close()
        return metadata

    def add_documents(self, documents: List[Document], project_name: str):
        '''
        Calculate Vectors for a set of documents and upload them to the database
        '''

        session = self.Session()

        # print the URLS of the documents th

        try:
            for doc in documents:
                document_metadata = self.tables.Documents(
                    title=doc.metadata['title'],
                    author=doc.metadata['author'],
                    file_type=doc.metadata['file_type'],
                    word_count=doc.metadata['word_count'],
                    language=doc.metadata['language'],
                    source=doc.metadata['source'],
                    content_type=doc.metadata['content_type'],
                    tags=doc.metadata['tags'],
                    summary=doc.metadata['summary'],
                    url=doc.metadata['url'],
                    project_name=doc.metadata['project_name'],
                    indexing_status=doc.metadata['indexing_status'],
                    priority=doc.metadata['priority'],
                    read_time=doc.metadata['read_time'],
                    creation_date=doc.metadata['creation_date'],
                    last_modified_date=doc.metadata['last_modified_date'],
                    upload_date=doc.metadata['upload_date'],
                    filename=doc.metadata['filename']
                )
                session.add(document_metadata)

            vectorstore = PGVector(
            embeddings=self.embeddings,
            collection_name=project_name,
            connection=self.engine,
            use_jsonb=True,
        )
            documents = chunk_content(documents)

            ids = [doc.metadata["uuid"] for doc in documents]
            # Remove the dates from the metadata
            for doc in documents:
                del doc.metadata['creation_date']
                del doc.metadata['last_modified_date']
                del doc.metadata['upload_date']

            result = vectorstore.add_documents(documents, ids=ids)

            session.commit()

        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding documents: {e}")
            return False
        finally:
            session.close()

    
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
        try:
            existing_project = session.query(self.tables.Project).filter_by(name=name).first()
            if existing_project:
                self.logger.error(f"Project with name '{name}' already exists. Skipping creation.")
                return existing_project.name

            new_project = self.tables.Project(name=name, description=description)
            session.add(new_project)
            session.commit()
            vectorstore = PGVector(
                embeddings=self.embeddings,
                collection_name=name,
                connection=self.engine,
                use_jsonb=True,
            )
            vectorstore.create_collection()
            self.supabase.storage.create_bucket(name)
            self.logger.info(f"Added new project: {name}")
            return new_project.name
        
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
        try:
            project = session.query(self.tables.Project).filter_by(name=project_name).first()
            if project:
                files = session.query(self.tables.Documents).filter_by(project_name=project_name, source="uploaded_file").all()
                for file in files:
                    self.supabase.storage.from_(project_name).remove([file.url])
                session.query(self.tables.IndexedLinks).filter_by(project_name=project_name).delete()
                session.query(self.tables.Documents).filter_by(project_name=project_name).delete()
                session.delete(project)
                session.commit()
                vectorstore = PGVector(
                    embeddings=self.embeddings,
                    collection_name=project_name,
                    connection=self.engine,
                    use_jsonb=True,
                )
                vectorstore.delete_collection()
                self.supabase.storage.delete_bucket(project_name)
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
            new_prompt = self.tables.Prompt(name=name, prompt=prompt_text)
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
            prompt = session.query(self.tables.Prompt).filter_by(id=prompt_id).first()
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
            prompt = session.query(self.tables.Prompt).filter_by(name=name).first()
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
            prompt = session.query(self.tables.Prompt).filter_by(id=prompt_id).first()
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
            prompts = session.query(self.tables.Prompt).all()
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
            new_key = self.tables.APIKeys(name=name, key=key)
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
            key = session.query(self.tables.APIKeys).filter_by(name=name).first()
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
            key = session.query(self.tables.APIKeys).filter_by(name=name).first()
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
            keys = session.query(self.tables.APIKeys).all()
            return [{"name": key.name, "key": key.key} for key in keys]
        finally:
            session.close()
        
    def add_links_to_index(self, status :str, links: List[str], base_url : str, project_name: str):
        '''
        Add a list of links to the database
        '''
        session = self.Session()
        self.logger.info(f"Adding links to confirm for base URL: {base_url}")
        try:
            for link in links:
                new_link = self.tables.IndexedLinks(url=link, status=status ,base_url=base_url, project_name=project_name)
                session.add(new_link)
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding links to confirm: {e}")
        finally:
            session.close()

    def remove_indexed_link(self, url: str, project_name: str):
        '''
        Remove an indexed link from the database
        '''
        session = self.Session()
        try:
            session.query(self.tables.IndexedLinks).filter_by(url=url, project_name=project_name).delete()
            session.commit()
            self.logger.info(f"Removed indexed link: {url}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error removing indexed link: {e}")
        finally:
            session.close()
            

    def get_indexing_status(self, project_name: str) -> List[dict] | None:
        '''
        Get the scrape status of all links for a project, grouped by project_name and status
        '''
        session = self.Session()
        self.logger.info(f"Getting scrape status for project: {project_name}")
        try:
            status = session.query(
                self.tables.IndexedLinks.project_name,
                self.tables.IndexedLinks.status,
                self.tables.IndexedLinks.base_url,
                func.max(self.tables.IndexedLinks.update_date).label('last_update')
            ).filter_by(project_name=project_name
            ).group_by(
                self.tables.IndexedLinks.project_name,
                self.tables.IndexedLinks.status,
                self.tables.IndexedLinks.base_url
            ).all()
            return [{"project_name": s.project_name, "status": s.status, "base_url": s.base_url, "last_update": s.last_update} for s in status]
        except Exception as e:
            self.logger.error(f"Error getting scrape status: {e}")
            return None
        finally:
            session.close()

    def get_links_to_confirm(self, project_name: str) -> List[dict] | None:
        '''
        Return a list of all links that can be confirmed for scraping
        '''
        session = self.Session()
        self.logger.info(f"Getting links to confirm for project: {project_name}")
        try:
            links = session.query(self.tables.IndexedLinks).filter_by(project_name=project_name, status="Confirm page import").all()
            return [{"url": l.url, "base_url": l.base_url} for l in links]
        except Exception as e:
            self.logger.error(f"Error getting links to confirm: {e}")
        finally:
            session.close()

    def update_indexed_link_status(self, url: str, project_name: str, status: str):
        '''
        Update the status of an indexed link
        '''
        session = self.Session()
        try:
            session.query(self.tables.IndexedLinks).filter_by(url=url, project_name=project_name).update({"status": status})
            session.commit()
            self.logger.debug(f"Updated indexed link status: {url}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating indexed link status: {e}")
        finally:
            session.close()

    def add_file(self, project_name: str, document_data: tuple):
        '''
        Add an uploaded file to the database

        args:
        document_data (tuple): List of tuples containing (bytes_data, filename)
        project_name (str): The name of the project to associate the document with


        '''
        filename = document_data[1]
        file_extension = filename.split(".")[-1]

        file_uuid = str(uuid.uuid4())
        path_on_supastorage = f"{str(file_uuid)}.{file_extension}"

        # Temporary store the file
        file_path = f"temp/{str(file_uuid)}/{filename}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(document_data[0])



        session = self.Session()
        try:
                # Caluculate MIME type
            if file_extension == "pdf":
                mime_type = "application/pdf"
            elif file_extension == "txt":
                mime_type = "text/plain"
            elif file_extension == "docx":
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif file_extension == "pptx":
                mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            else:
                mime_type = "text/html"

            with open(file_path, 'rb') as f:
                self.supabase.storage.from_(project_name).upload(
                    file=f,
                    path=path_on_supastorage,
                    file_options={
                        "content-type": mime_type
                    }
                    )
            session.commit()
            self.logger.info(f"Added uploaded file: {filename}")
            # Remove the temporary file and it's folder
            os.remove(file_path)
            os.rmdir(os.path.dirname(file_path))

        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding uploaded file: {e}")
        finally:
            session.close()
            return path_on_supastorage

    def list_files(self, project_name: str):
        '''
        List all uploaded files for a project
        '''
        session = self.Session()
        self.logger.info(f"Listing uploaded files for project: {project_name}")
        file_details = []
        try:
            files = session.query(self.tables.Documents).filter_by(project_name=project_name).all()
            for file in files:
                signed_url = self.supabase.storage.from_(project_name).create_signed_url(file.url, expires_in=3600)
                file_details.append(
                    {
                        "filename": file.filename,
                        "signed_download_url": signed_url['signedURL'],
                        "creation_date": file.creation_date,
                        "last_modified_date": file.last_modified_date
                    }
                )
            return file_details
        except Exception as e:
            self.logger.error(f"Error listing uploaded files: {e}")
        finally:
            session.close()

    def remove_file(self, project_name: str, file_name: str):
        '''
        Remove an uploaded file from the database
        '''
        session = self.Session()
        try:
            file_url = session.query(self.tables.Documents).filter_by(project_name=project_name, filename=file_name, source="uploaded_file").first()
            url = file_url.url
            self.supabase.storage.from_(project_name).remove([url])
            session.query(self.tables.Documents).filter_by(project_name=project_name, filename=file_name, source="uploaded_file").delete()
            self.remove_by_url(project_name, url)
            session.commit()
            self.logger.info(f"Removed uploaded file: {file_name}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error removing uploaded file: {e}")
        finally:
            session.close()