from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,field_validator
class IndexRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:UUID
    material_id:UUID
class SearchRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=1,max_length=2000)
    limit:int=Field(default=5,ge=1,le=8)
    @field_validator('query')
    @classmethod
    def nonempty(cls,value):
        if not value.strip():raise ValueError('Empty query')
        return value.strip()
