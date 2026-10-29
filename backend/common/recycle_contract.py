from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
class RecycleCommand(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:UUID
    expected_version:int=Field(ge=1,strict=True)
    kind:Literal['chapter','exercise','assignment']
    action:Literal['archive','restore','delete','clear']
    target_ids:list[UUID]=Field(min_length=1,max_length=1000)
    @model_validator(mode='after')
    def unique(self):
        if len(set(self.target_ids))!=len(self.target_ids): raise ValueError('duplicate ids')
        return self
class RecycleActivityArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['exercise','assignment']
    activity_id:UUID
