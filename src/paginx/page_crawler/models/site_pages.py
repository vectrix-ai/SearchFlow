from pydantic import BaseModel, Field
from typing import Optional

class PageData(BaseModel):
    title: Optional[str]
    hostname: Optional[str]
    date: Optional[str]
    fingerprint: Optional[str]
    id: Optional[str]
    license: Optional[str]
    comments: Optional[str]
    raw_text: Optional[str]
    text:Optional[str]
    language: Optional[str]
    image: Optional[str]
    pagetype: Optional[str]
    filedate: Optional[str]
    source: Optional[str]
    source_hostname: Optional[str] = Field(None, alias='source-hostname')
    excerpt: Optional[str]
    categories: Optional[str]
    tags: Optional[str]