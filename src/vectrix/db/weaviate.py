import os
from typing import Annotated, Optional, List, Tuple, Callable
from pydantic import BaseModel
from langchain.schema import Document
from langchain_core.runnables import chain
from langchain_core.documents import Document
import weaviate
from weaviate.classes.config import Configure
from weaviate.classes.query import MetadataQuery
from weaviate.classes.init import Auth

class Weaviate:
    """
    Manages the Weaviate client and provides methods for interacting with the vector database.
    """

    def __init__(self, collection_name: str = None) -> None:
        if os.getenv("ENVIROMENT") == "localhost":
            self.client = weaviate.connect_to_local()
        else:
            headers = {"X-Cohere-Api-Key": os.getenv('COHERE_API_KEY'),}
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=os.getenv("WEAVIATE_URL"),
                auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY")),
                headers=headers
            )
        if collection_name is not None:
            self.collection = self.client.collections.get(name=collection_name)
        
        else:
            self.collection = None 


    def create_collection(self, 
                          name: str, 
                          embedding_model: Annotated[str, "Ollama", "Cohere"],
                          model_url: str = None) -> None:
        """
        Creates a vectorizer module in Weaviate.
        """
        if embedding_model == "Ollama":
            self.client.collections.create(
                name=name,
                vectorizer_config=[
                    Configure.NamedVectors.text2vec_ollama(
                        name="content",
                        source_properties=["title", "content"],
                        model="mxbai-embed-large:335m",
                        api_endpoint=model_url
                    )
                ]
            )

        elif embedding_model == "Cohere":
            self.client.collections.create(
                name=name,
                vectorizer_config=[
                    Configure.NamedVectors.text2vec_cohere(
                        name="content",
                        source_properties=["title", "content"],
                        model="embed-multilingual-v3.0"
                    )
                ],
                # Additional parameters not shown
            )

        else:
            NotImplementedError

        self.collection = self.client.collections.get(name=name)

    def set_colleciton(self, name: str) -> None:
        """
        Sets the current collection to the specified name.
        """
        self.collection = self.client.collections.get(name=name)

        
    def list_collections(self) -> list:
        """
        Retrieves a list of all collections in the Weaviate database.

        Returns:
            list: A list of collections present in the Weaviate database.

        Note:
            This method uses the client's connections to list all available collections.
        """
        collections = []
        for connection in self.client.collections.list_all():
            collections.append(connection)
        return collections
    

    def remove_collection(self, name: str) -> None:
        """
        Removes a collection from the Weaviate database.

        Args:
            name (str): The name of the collection to be removed.

        Returns:
            None

        Raises:
            weaviate.exceptions.WeaviateException: If the collection doesn't exist or cannot be deleted.
        """
        self.client.collections.delete(name)


    def add_data(self, documents: List[Document]) -> None:
        """
        Adds a list of VectorDocument objects to the vector database.

        Args:
            documents (List[VectorDocument]): A list of VectorDocument objects to be added to the database.

        Raises:
            ValueError: If no collection is selected.
        """
        if self.collection is not None:
            with self.collection.batch.dynamic() as batch:
                for document in documents:
                    vector_object = {
                        "title": document.metadata['title'],
                        "url": document.metadata['url'],
                        "content": document.page_content,
                        "language": document.metadata['language'],
                        "source_type": document.metadata['source_type'],
                        "source_format" : document.metadata['source_format'],
                    }
                    batch.add_object(
                        properties=vector_object
                    )

        else:
            raise ValueError("No collection selected.")
        
    def list_metadata(self) -> list:
        '''
        Return a list of all objects, their URL and sour
        '''
        if self.collection is not None:
            items = [{"url": items.properties.get('url'), 
                      "source_type": items.properties.get('source_type'),
                      "source_format" : items.properties.get('source_format')} for items in self.collection.iterator()]
            return items

        
    def close(self) -> None:
        """
        Closes the connection to the Weaviate database.
        """
        self.client.close()

    def get_retriever(self) -> Callable[[str], List[Tuple[Document, str]]]:
        """
        Create and return a retriever function for Weaviate vector store.

        Returns:
            Callable[[str], List[Tuple[Document, float]]]: A function that performs
            hybrid search using Weaviate vector store.
        """
        @chain
        def retriever(query: str) -> List[Document]:
            """
            Perform hybrid search using Weaviate vector store.

            Args:
                query (str): The search query.

            Returns:
                List[Tuple[Document, float]]: A list of tuples, each containing
                a Document and its relevance score.
            """
            if self.collection is None:
                raise ValueError("No collection selected.")
            
            results = self.collection.query.hybrid(
                query=query,
                limit=2,
                return_metadata=MetadataQuery(score=True, explain_score=True),
            )
            return [
                Document(
                    page_content=result.properties['content'],
                    metadata={
                        "title": result.properties['title'], 
                        "url": result.properties['url'], 
                        "source_type": result.properties['source_type'],
                        "source_format": result.properties['source_format'],
                        "uuid": str(result.uuid),
                        "score": result.metadata.score,
                        }
                )
                for result in results.objects
            ]

        return retriever
    

    def info(self) -> dict:
        """
        Retrieves information about the Weaviate server and the installed modules
        """

        return self.client.get_meta()
