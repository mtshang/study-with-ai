from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass


class RuntimeSchema(Base):
    """Migration/readiness marker only; agent execution is not implemented yet."""
    __tablename__="runtime_schema"
    id: Mapped[int] = mapped_column(primary_key=True)
