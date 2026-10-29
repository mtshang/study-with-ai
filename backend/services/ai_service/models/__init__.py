from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass


class RuntimeSchema(Base):
    """Initial migration/readiness marker; chat runtime tables are defined separately."""
    __tablename__="runtime_schema"
    id: Mapped[int] = mapped_column(primary_key=True)

from .memory import PersonaDefault, CoursePersona, CourseMemory
from .runtime import AIProfile, ChatRun, ToolProposal
from .assistants import CourseAgentState, AssistantTask, RunContext

from .recovery import AgentJob,AgentStep,GraphCheckpoint,GraphWrite

from .extensions import Extension, CourseExtensions, MCPInvocation

from .sandbox import SandboxRun
