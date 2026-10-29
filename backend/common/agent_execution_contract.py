"""Bounded, credential-free wire contract for temporary Agent execution."""
import base64,re
from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

MAX_TOTAL=5*1024*1024
def path_name(value):
    if not value or len(value)>160 or '\\' in value or ':' in value or '\x00' in value:raise ValueError('Invalid path')
    parts=value.split('/')
    if any(not p or p in ('.','..') or p.endswith((' ','.')) or re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',p,re.I) for p in parts):raise ValueError('Invalid path')
    return value

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class PackedFile(Strict):
    path:str
    content:str=Field(max_length=MAX_TOTAL*4//3+4)
    @field_validator('path')
    @classmethod
    def safe(cls,v):return path_name(v)
    @field_validator('content')
    @classmethod
    def encoded(cls,v):
        if len(base64.b64decode(v,validate=True))>MAX_TOTAL:raise ValueError('File too large')
        return v

class AgentExecutionInput(Strict):
    id:UUID
    code:str=Field(default='',max_length=12000)
    script:str|None=None
    arguments:list[str]=Field(default_factory=list,max_length=20)
    inputs:list[PackedFile]=Field(default_factory=list,max_length=20)
    skill:list[PackedFile]=Field(default_factory=list,max_length=256)
    @model_validator(mode='after')
    def bounded(self):
        if bool(self.code.strip())==bool(self.script):raise ValueError('Choose code or script')
        if self.script:
            path_name(self.script)
            if not self.script.endswith('.py') or self.script not in [f.path for f in self.skill]:raise ValueError('Missing Python script')
        if any(len(a)>1000 or '\x00' in a for a in self.arguments):raise ValueError('Invalid arguments')
        if sum(len(base64.b64decode(f.content)) for f in self.inputs+self.skill)>MAX_TOTAL:raise ValueError('Inputs too large')
        for group in (self.inputs,self.skill):
            names=[f.path.casefold() for f in group]
            if len(names)!=len(set(names)) or any(a.startswith(b+'/') for a in names for b in names if a!=b):raise ValueError('Duplicate paths')
        return self

class AgentExecutionResult(Strict):
    status:Literal['completed','runtime_error','timeout','unavailable','interrupted','running']
    stdout:str=Field(default='',max_length=32768)
    stderr:str=Field(default='',max_length=32768)
    exit_code:int|None=None
    files:list[PackedFile]=Field(default_factory=list,max_length=20)
    duration_ms:int=Field(default=0,ge=0)
    @model_validator(mode='after')
    def bounded(self):
        names=[f.path.casefold() for f in self.files]
        if len(names)!=len(set(names)) or sum(len(base64.b64decode(f.content)) for f in self.files)>MAX_TOTAL:raise ValueError('Invalid outputs')
        return self
