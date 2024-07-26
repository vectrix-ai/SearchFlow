from typing import Optional
from pydantic import BaseModel, Field

class VectorDocument(BaseModel):
    """
    Data model for storing chunks of text and their metadata.
    Can be ingested by the Vectordb class.
    """
    title: str
    url: str
    content: str
    type: str
    NER: Optional[str] = None

class FileObject(BaseModel):
    '''
    A physical file object that can be processed for chunking and processing.
    '''
    file_path: str
    file_type: str
    file_name: str
    url: Optional[str] = None

class WebPageData(BaseModel):
    '''
    Content of an extracted webpage.
    '''
    content: dict = {
        "title": Optional[str],
        "hostname": Optional[str],
        "date": Optional[str],
        "fingerprint": Optional[str],
        "id": Optional[str],
        "license": Optional[str],
        "comments": Optional[str],
        "raw_text": Optional[str],
        "text": Optional[str],
        "language": Optional[str],
        "image": Optional[str],
        "pagetype": Optional[str],
        "filedate": Optional[str],
        "source": Optional[str],
        "source_hostname": Optional[str],
        "excerpt": Optional[str],
        "categories": Optional[str],
        "tags": Optional[str]
    }
    metadata: dict = {}
    source_hostname: Optional[str] = Field(None, alias='source-hostname')
