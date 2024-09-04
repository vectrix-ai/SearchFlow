from typing import Literal, Optional, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain import hub
from searchflow.models import DocumentMetaData
from langchain_core.documents import Document
from pydantic import BaseModel
from searchflow import logger

class ExtractionObject(BaseModel):
    title: str
    content: str
    url: str
    project_name: str
    file_type: Literal["webpage", "pdf", "docx", "txt", "csv", "other"]
    source: Literal["webpage", "uploaded_file", "OneDrive", "Notion", "chrome_extension"]
    filename: Optional[str] = ""
    creation_date: Optional[datetime] = None
    last_modified_date: Optional[datetime] = None
    

class ExtractMetaData:
    '''
    This class is used to extract information from a document.

    args:
        llm: langchain llm object
    '''
    def __init__(self):
        self.llm_with_tools = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompt = hub.pull("entity_extraction")
        self.logger = logger.setup_logger('ExtractMetaData')

    @staticmethod
    def _calculate_word_count(text: str) -> int:
        return len(text.split())
    
    @staticmethod
    def _calculate_read_time(word_count: int) -> float:
        return word_count / 200

    def extract(self, documents: List[ExtractionObject]) -> List[Document]:
        self.logger.info(f"Extracting metadata from {len(documents)} documents")
        chain = self.prompt | self.llm_with_tools
        content_list = [{"content" : doc.content} for doc in documents]
        responses =  chain.batch(content_list)

        results = []

        # Merge the responses with the documents
        for doc, response in zip(documents, responses):
            doc_metadata = DocumentMetaData(
                title=doc.title,
                author=response.get("author", ""),
                file_type=doc.file_type,
                word_count=self._calculate_word_count(doc.content),
                language=response.get("language", ""),
                source=doc.source,
                content_type=response.get("content_type", ""),
                tags=response.get("tags", ""),
                summary=response.get("summary", ""),
                url=doc.url,
                project_name=doc.project_name,
                read_time=self._calculate_read_time(self._calculate_word_count(doc.content)),
                creation_date=doc.creation_date,
                last_modified_date=doc.last_modified_date,
                filename=doc.filename
            )
            results.append(Document(
                page_content=doc.content,
                metadata=doc_metadata.model_dump()
            ))
        return results