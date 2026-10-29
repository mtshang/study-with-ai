from sqlalchemy import String, Text, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from . import Base, utcnow

class CourseAgentState(Base):
    __tablename__ = 'course_agent_states'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    course_id: Mapped[str] = mapped_column(String(36))
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    change_sequence: Mapped[int] = mapped_column(Integer, default=0)

class AssistantTask(Base):
    __tablename__ = 'assistant_tasks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey('chat_runs.id',ondelete='CASCADE'), index=True,nullable=True)
    purpose: Mapped[str] = mapped_column(String(24),default='delegated')
    submission_id: Mapped[str | None] = mapped_column(String(36),nullable=True,unique=True)
    payload: Mapped[dict | None] = mapped_column(JSON,nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    course_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(100))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default='queued')
    result: Mapped[str] = mapped_column(Text, default='')
    error: Mapped[str] = mapped_column(String(300), default='')
    consumed_by: Mapped[str | None] = mapped_column(ForeignKey('chat_runs.id',ondelete='SET NULL'), nullable=True)
    created_at: Mapped[object] = mapped_column(DATETIME(fsp=6),default=utcnow)
    finished_at: Mapped[object | None] = mapped_column(DATETIME(fsp=6),nullable=True)

class RunContext(Base):
    __tablename__ = 'run_contexts'
    run_id: Mapped[str] = mapped_column(ForeignKey('chat_runs.id',ondelete='CASCADE'),primary_key=True)
    # Append ordered input batches; commit together with inbox acknowledgement.
    batches: Mapped[list] = mapped_column(JSON,default=list)
