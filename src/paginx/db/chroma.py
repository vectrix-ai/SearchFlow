from langchain_chroma import Chroma as ChromaBase
from langchain_community.vectorstores import utils
from langchain_core.documents.base import Document


class Chroma:
    def __init__(self, embedding_function) -> None:
        self.embedding_function = embedding_function

    def create_db(self, pages: list, persist_directory: str = None):
        """
        Creates a ChromaBase database from a list of Document objects.

        Args:
            pages (list): A list of Document objects representing the pages to be included in the database.
            persist_directory (str, optional): The directory path where the database should be persisted. Defaults to None.

        Returns:
            ChromaBase: The created ChromaBase database.

        Raises:
            TypeError: If any element in the 'pages' list is not of type Document.
        """
        if not all(isinstance(page, Document) for page in pages):
            raise TypeError("All elements in pages must be of type Document")

        def extract_content_and_ids(docs):
            page_contents = []
            ids = []

            for doc in docs:
                page_contents.append(doc.page_content)
                ids.append(doc.metadata['uuid'])
            
            return page_contents, ids

        page_contents, ids = extract_content_and_ids(pages)
        simple_contents = utils.filter_complex_metadata(pages)
        if persist_directory:
            return ChromaBase.from_documents(simple_contents, self.embedding_function, ids=ids, persist_directory=persist_directory)
        
        return ChromaBase.from_documents(simple_contents, self.embedding_function, ids=ids)
    
    def load_db(self, persist_directory: str):
        """
        Loads the Chroma database from the specified persist directory.

        Args:
            persist_directory (str): The directory path where the Chroma database is stored.

        Returns:
            Chroma: The loaded Chroma database.

        """
        db = ChromaBase(persist_directory=persist_directory, embedding_function=self.embedding_function)
        return db

