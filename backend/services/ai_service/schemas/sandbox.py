from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator,field_validator
from common.agent_execution_contract import path_name
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class InputFile(Strict):
    kind:Literal['material','artifact']
    id:UUID
    name:str
    @field_validator('name')
    @classmethod
    def safe(cls,v):return path_name(v)
class SandboxCommand(Strict):
    title:str=Field(min_length=1,max_length=120)
    code:str=Field(default='',max_length=12000)
    inputs:list[InputFile]=Field(default_factory=list,max_length=10)
    skill_id:UUID|None=None
    skill_revision:int|None=Field(default=None,ge=1)
    script:str|None=None
    arguments:list[str]=Field(default_factory=list,max_length=20)
    @model_validator(mode='after')
    def choice(self):
        if bool(self.code.strip())==bool(self.script):raise ValueError('Choose code or Skill script')
        if self.script:
            path_name(self.script)
            if not self.skill_id or not self.skill_revision or not self.script.endswith('.py'):raise ValueError('Missing Skill version/script')
        elif self.skill_id or self.skill_revision:raise ValueError('Skill requires script')
        return self
class ReadArtifact(Strict):
    id:UUID
    offset:int=Field(default=0,ge=0)
