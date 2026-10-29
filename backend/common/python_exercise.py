from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class PythonCase(BaseModel):
    model_config=ConfigDict(extra='forbid')
    stdin:str=Field(default='',max_length=4000)
    expected_stdout:str=Field(max_length=4000)

class PythonExercise(BaseModel):
    model_config=ConfigDict(extra='forbid')
    language:Literal['python']='python'
    starter_code:str=Field(default='',max_length=10000)
    cases:list[PythonCase]=Field(min_length=1,max_length=3)
