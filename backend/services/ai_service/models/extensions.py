from sqlalchemy import String, Integer, JSON, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from . import Base, utcnow


class Extension(Base):
    __tablename__ = 'extensions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(100))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[object] = mapped_column(DATETIME(fsp=6), default=utcnow)


class CourseExtensions(Base):
    __tablename__ = 'course_extensions'
    owner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[list] = mapped_column(JSON, default=list)


class MCPInvocation(Base):
    __tablename__ = 'mcp_invocations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    course_id: Mapped[str] = mapped_column(String(36), index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    extension_id: Mapped[str] = mapped_column(String(36), index=True)
    extension_revision: Mapped[int] = mapped_column(Integer)
    tool: Mapped[str] = mapped_column(String(128))
    effect: Mapped[str] = mapped_column(String(12))
    arguments: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[object] = mapped_column(DATETIME(fsp=6), default=utcnow)
