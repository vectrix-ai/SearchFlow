from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime, UTC

class DocumentMetaData(BaseModel):
    title: str
    author: Optional[str] = None
    file_type: Literal["webpage", "pdf", "docx", "txt", "csv", "other"]
    word_count: int 
    language: Optional[str] = None
    source: Literal["webpage", "uploaded_file", "OneDrive", "Notion", "chrome_extension"]
    content_type: Optional[str] = None
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    url: str
    project_name: str
    indexing_status: Optional[str] = None
    filename: Optional[str] = None
    priority: Optional[int] = None
    read_time: float
    creation_date: Optional[datetime] = None
    last_modified_date: Optional[datetime] = None
    upload_date: datetime = Field(default_factory=lambda: datetime.now(UTC))