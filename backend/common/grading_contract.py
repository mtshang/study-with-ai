"""Shared wire schema, not cross-service database access."""
from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field,model_validator

class GradeResult(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mastery:Literal['mastered','partial','needs_practice']
    reason:str=Field(min_length=1,max_length=1600)
    evidence:list[Annotated[str,Field(min_length=1,max_length=500)]]=Field(min_length=1,max_length=4)
    suggestions:list[Annotated[str,Field(min_length=1,max_length=500)]]=Field(min_length=1,max_length=4)
    sample_answer:str=Field(min_length=1,max_length=2000)
    @model_validator(mode='after')
    def not_blank(self):
        if any(not v.strip() for v in [self.reason,self.sample_answer,*self.evidence,*self.suggestions]): raise ValueError('Empty grading field')
        return self

class GradeUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    input_hash:str=Field(pattern=r'^[0-9a-f]{64}$')
    status:Literal['running','failed','completed']
    result:GradeResult|None=None
    model:str=Field(default='',max_length=120)
    error:str=Field(default='',max_length=300)
    @model_validator(mode='after')
    def complete(self):
        if (self.status=='completed')!=(self.result is not None): raise ValueError('Result/status mismatch')
        if self.status=='completed' and not self.model.strip(): raise ValueError('Model required')
        return self

MASTERY={'mastered':'基本掌握','partial':'部分掌握','needs_practice':'需要再练'}
