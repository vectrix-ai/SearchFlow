from datetime import datetime
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import pytz

Base = declarative_base()

class PromptManager:
    """
    A class for managing prompts in a database.

    This class provides methods to add, update, remove, and retrieve prompts
    stored in a SQL database using SQLAlchemy ORM.

    Attributes:
        engine: SQLAlchemy database engine
        Session: SQLAlchemy session factory

    Methods:
        add_prompt: Add a new prompt to the database
        update_prompt: Update an existing prompt in the database
        remove_prompt: Remove a prompt from the database
        get_all_prompts: Retrieve all prompts from the database
    """
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Create the table if it doesn't exist
        Base.metadata.create_all(self.engine)

    class Prompt(Base):
        __tablename__ = 'prompts'

        id = Column(Integer, primary_key=True)
        name = Column(String(255), nullable=False)
        prompt = Column(Text, nullable=False)
        creation_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))
        update_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), onupdate=lambda: datetime.now(pytz.UTC))

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