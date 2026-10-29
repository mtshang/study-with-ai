from sqlalchemy import String, Text, Integer, JSON, Boolean
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column
from . import Base, utcnow

class PersonaDefault(Base):
    __tablename__='persona_defaults'
    owner_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    revision: Mapped[int]=mapped_column(Integer,primary_key=True)
    prompt: Mapped[str]=mapped_column(Text)
    created_at: Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)

class CoursePersona(Base):
    __tablename__='course_personas'
    owner_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    course_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    prompt: Mapped[str]=mapped_column(Text)
    version: Mapped[int]=mapped_column(Integer,default=1)
    source_revision: Mapped[int]=mapped_column(Integer,default=0)

class CourseMemory(Base):
    __tablename__='course_memories'
    owner_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    course_id: Mapped[str]=mapped_column(String(36),primary_key=True)
    key: Mapped[str]=mapped_column(String(80),primary_key=True)
    category: Mapped[str]=mapped_column(String(24))
    content: Mapped[str]=mapped_column(Text)
    evidence: Mapped[dict]=mapped_column(JSON)
    version: Mapped[int]=mapped_column(Integer,default=1)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    updated_at: Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
