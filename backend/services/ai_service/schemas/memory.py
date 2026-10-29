from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

class PersonaUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version:int=Field(ge=0)
    prompt:str=Field(min_length=1,max_length=3000)
    @field_validator('prompt')
    @classmethod
    def clean(cls,value):
        if not value.strip():raise ValueError('Empty persona')
        return value.strip()

class MemoryCommand(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key:str=Field(pattern=r'^[a-z][a-z0-9_.-]{0,79}$')
    expected_version:int=Field(ge=0)
    action:Literal['remember','retire']='remember'
    category:Literal['student_statement','ai_judgment']
    content:str=Field(min_length=1,max_length=600)
    evidence_quote:str=Field(min_length=2,max_length=1000)
    evidence_call_id:str|None=Field(default=None,max_length=200)
    conflict:bool=False
    affected:list[Literal['chapters','exercises','assignments']]=Field(default_factory=list,max_length=3)
    affected_chapters:list[UUID]=Field(default_factory=list,max_length=20)
    question:str=Field(min_length=1,max_length=500)
    @field_validator('content','question','evidence_quote')
    @classmethod
    def clean(cls,value):
        if not value.strip():raise ValueError('Empty field')
        return value.strip()
