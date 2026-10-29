from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

from sqlalchemy import Boolean, Integer, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT, DATETIME

class CourseRecord(Base):
    __tablename__ = "courses"
    creation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(80))
    goal: Mapped[str] = mapped_column(String(1000), default="")
    category: Mapped[str] = mapped_column(String(40), default="自主学习")
    color: Mapped[str] = mapped_column(String(16), default="purple")
    icon: Mapped[str] = mapped_column(String(16), default="book")
    source: Mapped[str] = mapped_column(String(16), default="user")
    template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    current_chapter_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    change_seq: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class ChapterRecord(Base):
    __tablename__ = "chapters"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"))
    position: Mapped[int] = mapped_column(Integer)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="user")

class CourseRevision(Base):
    __tablename__ = "course_revisions"
    __table_args__ = (UniqueConstraint("course_id", "version", name="uq_course_revision_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(String(200))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActivityRecord(Base):
    __tablename__ = "activities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))
    source: Mapped[str] = mapped_column(String(16), default="user")
    questions: Mapped[list] = mapped_column(JSON)
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(DATETIME(fsp=6), "mysql"), default=utcnow)

class SubmissionRecord(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("activity_id", "request_id", name="uq_submission_request"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    request_hash: Mapped[str] = mapped_column(String(64))
    answers: Mapped[dict] = mapped_column(JSON)
    snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(DATETIME(fsp=6), "mysql"), default=utcnow)


class MaterialRecord(Base):
    __tablename__ = "materials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"))
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(DATETIME(fsp=6), "mysql"), default=utcnow)

class CourseChange(Base):
    __tablename__="course_changes"
    __table_args__=(UniqueConstraint("course_id","sequence",name="uq_course_change_sequence"),)
    id: Mapped[str] = mapped_column(String(36),primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id",ondelete="CASCADE"),index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    course_version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(36))
    summary: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(DATETIME(fsp=6),"mysql"),default=utcnow)
