from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional, List

class Entity(BaseModel):
    entity_type: Optional[str] = Field(description="The type of the entity, for example 'person', 'location', 'organization' etc.")
    entity_name: Optional[str] = Field(description="The name of the entity, for example 'John Doe', 'New York', 'Apple Inc.' etc.")

# Define your desired data structure.
class NERExtraction(BaseModel):
    entity_list: List[Entity] = Field(description="List of entities extracted from the text")
    language: str = Field(description="The language of the text")
    category: str = Field(description="Return the subject what this text excaclty is about")