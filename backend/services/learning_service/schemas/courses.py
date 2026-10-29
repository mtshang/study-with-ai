from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class CourseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    title: str = Field(min_length=1, max_length=80)
    goal: str = Field(default="", max_length=1000)
    template_id: int | None = Field(default=None, ge=0, le=2, strict=True)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip(): raise ValueError("课程名不能为空")
        return value.strip()

class ChapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=200)
    content: str = Field(default="", max_length=20000)
    read: bool = Field(default=False, strict=True)
    archived: bool = Field(default=False, strict=True)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip(): raise ValueError("章节名不能为空")
        return value.strip()

class CourseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=80)
    goal: str = Field(max_length=1000)
    archived: bool = Field(strict=True)
    currentChapterId: UUID | None = None
    chapters: list[ChapterInput] = Field(max_length=100)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip(): raise ValueError("课程名不能为空")
        return value.strip()

    @model_validator(mode="after")
    def check_chapters(self):
        ids=[ch.id for ch in self.chapters]
        if len(ids)!=len(set(ids)): raise ValueError("章节不能重复")
        if self.currentChapterId is not None and not any(ch.id==self.currentChapterId and not ch.archived for ch in self.chapters):
            raise ValueError("当前章节必须属于本课且未归档")
        return self
