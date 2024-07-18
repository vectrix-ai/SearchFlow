import os
from typing import Literal, List, Tuple, Callable

from langchain_cohere import CohereEmbeddings
from langchain_core.runnables import chain
from langchain.schema import Document
import weaviate
from weaviate.classes.query import MetadataQuery
from paginx.db.chroma import Chroma

class Retriever:
    """
    A class to handle document retrieval using different vector stores.

    This class provides an interface to retrieve documents using either
    Chroma or Weaviate as the underlying vector store.

    Attributes:
        retriever_type (Literal['weaviate', 'chroma']): The type of vector store to use.
    """

    def __init__(self, retriever_type: Literal['weaviate', 'chroma']):
        """
        Initialize the Retriever with a specified vector store type.

        Args:
            retriever_type (Literal['weaviate', 'chroma']): The type of vector store to use.
        """
        self.retriever_type = retriever_type

    def get_retriever(self) -> Callable[[str], List[Tuple[Document, str]]]:
        """
        Get the appropriate retriever function based on the initialized type.

        Returns:
            Callable[[str], List[Tuple[Document, float]]]: A function that takes a query string
            and returns a list of tuples, each containing a Document and its relevance score.

        Raises:
            ValueError: If an unsupported retriever type is specified.
        """
        if self.retriever_type == 'chroma':
            return self._get_chroma_retriever()
        elif self.retriever_type == 'weaviate':
            return self._get_weaviate_retriever()
        else:
            raise ValueError(f"Unsupported retriever type: {self.retriever_type}")

    def _get_chroma_retriever(self) -> Callable[[str], List[Tuple[Document, str]]]:
        """
        Create and return a retriever function for Chroma vector store.

        Returns:
            Callable[[str], List[Tuple[Document, float]]]: A function that performs
            similarity search using Chroma vector store.

        Raises:
            ValueError: If the CHROMA_DB_LOCATION environment variable is not set.
        """
        chroma = Chroma(CohereEmbeddings())
        db_location = os.getenv("CHROMA_DB_LOCATION")
        if not db_location:
            raise ValueError("CHROMA_DB_LOCATION environment variable is not set")
        vectorstore = chroma.load_db(db_location)

        @chain
        def retriever(query: str) -> List[Tuple[Document, str]]:
            """
            Perform similarity search using Chroma vector store.

            Args:
                query (str): The search query.

            Returns:
                List[Tuple[Document, float]]: A list of tuples, each containing
                a Document and its relevance score.
            """
            docs_and_scores = vectorstore.similarity_search_with_score(query)
            for doc, score in docs_and_scores:
                doc.metadata["score"] = score
            return docs_and_scores

        return retriever

    def _get_weaviate_retriever(self) -> Callable[[str], List[Tuple[Document, str]]]:
        """
        Create and return a retriever function for Weaviate vector store.

        Returns:
            Callable[[str], List[Tuple[Document, float]]]: A function that performs
            hybrid search using Weaviate vector store.
        """
        client = weaviate.connect_to_local()
        vectrix = client.collections.get("Vectrix")

        @chain
        def retriever(query: str) -> List[Tuple[Document, str | None]]:
            """
            Perform hybrid search using Weaviate vector store.

            Args:
                query (str): The search query.

            Returns:
                List[Tuple[Document, float]]: A list of tuples, each containing
                a Document and its relevance score.
            """
            results = vectrix.query.hybrid(
                query=query,
                limit=3,
                alpha=0.8,
                return_metadata=MetadataQuery(explain_score=True),
                query_properties=['content']
            )
            return [
                (Document(
                    page_content=result.properties['content'],
                    metadata={"title": result.properties['title'], "url": result.properties['url'], "type": result.properties['type']}
                ), result.metadata.explain_score)
                for result in results.objects
            ]

        return retriever