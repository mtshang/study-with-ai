from sqlalchemy import String, Text, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from . import Base, utcnow

class AIProfile(Base):
    __tablename__ = 'ai_profiles'
    owner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    permission: Mapped[str] = mapped_column(String(16), default='manual')

class ChatRun(Base):
    __tablename__ = 'chat_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    course_id: Mapped[str] = mapped_column(String(36), index=True)
    # A nullable unique slot allows only one active reply per course, across requests.
    active_key: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    trigger: Mapped[str] = mapped_column(String(16), default='user')
    prompt: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(24), default='running')
    progress: Mapped[str] = mapped_column(String(200), default='准备读取课程')
    error: Mapped[str] = mapped_column(String(300), default='')
    created_at: Mapped[object] = mapped_column(DATETIME(fsp=6), default=utcnow)
    updated_at: Mapped[object] = mapped_column(DATETIME(fsp=6), default=utcnow)

class ToolProposal(Base):
    __tablename__ = 'tool_proposals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('chat_runs.id', ondelete='CASCADE'), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default='pending')
    error: Mapped[str] = mapped_column(String(300), default='')
