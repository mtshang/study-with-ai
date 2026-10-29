from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator

class ExecutionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:UUID
    code:str=Field(min_length=1,max_length=10000)
    stdin:str=Field(default='',max_length=4000)
    @field_validator('code')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('代码不能为空')
        return value

class ExecutionResult(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:Literal['completed','runtime_error','timeout','output_limit','unavailable']
    stdout:str=Field(max_length=32768)
    stderr:str=Field(max_length=32768)
    exit_code:int|None=None
    duration_ms:int=Field(ge=0)
    output_truncated:bool=False
