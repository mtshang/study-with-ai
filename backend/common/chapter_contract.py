"""Shared typed commands; clients cannot choose identity, source or completion state."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

class ChapterOperation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['add','update','move','archive','restore']
    chapter_id:UUID|None=None
    title:str|None=Field(default=None,min_length=1,max_length=100)
    description:str|None=Field(default=None,max_length=200)
    content:str|None=Field(default=None,max_length=20000)
    after_id:UUID|None=None
    @model_validator(mode='after')
    def validate_action(self):
        fields=self.model_fields_set
        if self.title is not None and not self.title.strip(): raise ValueError('blank title')
        if self.action=='add':
            if self.chapter_id is not None or not self.title: raise ValueError('add requires title and no id')
        else:
            if self.chapter_id is None: raise ValueError('existing chapter required')
            if self.action=='update':
                if not any(getattr(self,k) is not None for k in ('title','description','content')): raise ValueError('empty update')
                if 'after_id' in fields: raise ValueError('use move separately')
            else:
                if any(getattr(self,k) is not None for k in ('title','description','content')): raise ValueError('unexpected content')
                if self.action=='move' and 'after_id' not in fields: raise ValueError('move requires after_id; null means first')
                if self.action!='move' and 'after_id' in fields: raise ValueError('unexpected location')
        return self

class ChapterPlan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    summary:str=Field(min_length=1,max_length=120)
    operations:list[ChapterOperation]=Field(min_length=1,max_length=10)
    @model_validator(mode='after')
    def nonblank(self):
        if not self.summary.strip(): raise ValueError('blank summary')
        return self

class ChapterCommand(ChapterPlan):
    id:UUID
    expected_version:int=Field(ge=1,strict=True)

class ChapterRead(BaseModel):
    model_config=ConfigDict(extra='forbid')
    chapter_id:UUID
