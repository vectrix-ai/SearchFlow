from paginx.db.chroma import Chroma
from langchain_cohere import CohereEmbeddings
from langchain_core.runnables import chain
from typing import Literal, List, Tuple
import os
from langchain.schema import Document
import weaviate
from weaviate.classes.query import MetadataQuery


class Retriever:
    def __init__(self, retriever: Literal['weaviate', 'chroma']):
        self.retriever = retriever


    def get_retriever(self):
        if self.retriever == 'chroma':
            chroma = Chroma(CohereEmbeddings())
            self.vectorstore = chroma.load_db(os.getenv("CHROMA_DB_LOCATION"))
            @chain
            def retriever(query: str) -> List[Tuple[Document, float]]:
                docs_and_scores = self.vectorstore.similarity_search_with_score(query)
                for doc, score in docs_and_scores:
                    print(score)
                    doc.metadata["score"] = score
                return docs_and_scores
            return retriever

        elif self.retriever == 'weaviate':
            client = weaviate.connect_to_local()
            collection = client.collections.get("Vectrix")

            @chain
            def retriever(query: str) -> List[Tuple[Document, float]]:
                docs_and_scores = vectrix.query.hybrid(query=query, limit=3, alpha=0.5, return_metadata=MetadataQuery(explain_score=True))
                for doc in docs_and_scores:
                    doc.metadata["score"] = doc.score






