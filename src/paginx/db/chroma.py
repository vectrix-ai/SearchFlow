from langchain_chroma import Chroma as ChromaBase
from langchain_cohere import CohereEmbeddings
from langchain_community.vectorstores import utils
from langchain_core.documents.base import Document


class Chroma:
    def __init__(self, pages: list) -> None:
        if not all(isinstance(page, Document) for page in pages):
            raise TypeError("All elements in pages must be of type Document")
        self.pages = pages
        self.embedding_function = CohereEmbeddings()

    def return_db_object(self):

        def extract_content_and_ids(docs):
            page_contents = []
            ids = []

            for doc in docs:
                page_contents.append(doc.page_content)
                ids.append(doc.metadata['uuid'])
            
            return page_contents, ids

        page_contents, ids = extract_content_and_ids(self.pages)
        simple_contents = utils.filter_complex_metadata(self.pages)
        return ChromaBase.from_documents(simple_contents, self.embedding_function, ids=ids)

