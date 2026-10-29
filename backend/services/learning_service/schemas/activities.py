from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from common.python_exercise import PythonExercise

class QuestionInput(BaseModel):
    python:PythonExercise|None=None
    model_config=ConfigDict(extra="forbid")
    prompt:str=Field(min_length=1,max_length=3000)
    options:list[Annotated[str,Field(min_length=1,max_length=200)]] | None=Field(default=None,min_length=2,max_length=10)
    correct:str | None=Field(default=None,max_length=200)
    explanation:str=Field(default="",max_length=3000)

    @model_validator(mode="after")
    def validate_question(self):
        self.prompt=self.prompt.strip()
        if not self.prompt: raise ValueError("题目不能为空")
        if self.python is not None and (self.options is not None or self.correct is not None):raise ValueError('Python题不能同时设置选项或选择答案')
        if self.options is not None:
            self.options=[option.strip() for option in self.options]
            if any(not option for option in self.options) or len(set(self.options))!=len(self.options):
                raise ValueError("选项不能为空或重复")
            if self.correct not in self.options: raise ValueError("客观题必须选择有效的参考答案")
        elif self.correct is not None:
            raise ValueError("开放题不能按字符串相等自动批改")
        return self

class ActivityCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id:UUID
    source:Literal['user','ai']='user'
    expected_version:int|None=Field(default=None,ge=1)
    kind:Literal["exercise","assignment"]
    title:str=Field(min_length=1,max_length=200)
    description:str=Field(default="",max_length=2000)
    chapter_id:UUID | None=None
    questions:list[QuestionInput]=Field(min_length=1,max_length=10)

    @model_validator(mode="after")
    def validate_activity(self):
        self.title=self.title.strip()
        if not self.title: raise ValueError("名称不能为空")
        if self.kind=="exercise" and len(self.questions)!=1: raise ValueError("练习只能有一道题")
        if self.kind=="assignment" and len(self.questions)<2: raise ValueError("作业至少两道题")
        if self.kind!='exercise' and any(q.python is not None for q in self.questions):raise ValueError('Python第一版仅支持单道练习')
        return self

class SubmissionInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    request_id:UUID
    attachments:list[UUID]=Field(default_factory=list,max_length=5)

    @field_validator("attachments")
    @classmethod
    def unique_attachments(cls,items):
        if len(set(items))!=len(items): raise ValueError("附件不能重复")
        return items

    answers:dict[str,Annotated[str,Field(min_length=1,max_length=10000)]]=Field(min_length=1,max_length=10)

    @field_validator("answers")
    @classmethod
    def not_empty(cls,answers):
        if any(not answer.strip() for answer in answers.values()): raise ValueError("答案不能为空")
        return answers
