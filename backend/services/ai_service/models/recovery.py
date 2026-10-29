from sqlalchemy import String,Text,Integer,JSON,ForeignKey
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped,mapped_column
from . import Base,utcnow
class AgentJob(Base):
    __tablename__='agent_jobs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    owner_id:Mapped[str]=mapped_column(String(36),index=True)
    course_id:Mapped[str]=mapped_column(String(36),index=True)
    kind:Mapped[str]=mapped_column(String(16))
    credential:Mapped[str]=mapped_column(Text)
    origin:Mapped[str]=mapped_column(String(200))
    status:Mapped[str]=mapped_column(String(24),default='queued',index=True)
    generation:Mapped[int]=mapped_column(Integer,default=0)
    recoveries:Mapped[int]=mapped_column(Integer,default=0)
    lease_owner:Mapped[str|None]=mapped_column(String(36),nullable=True)
    lease_until:Mapped[object|None]=mapped_column(DATETIME(fsp=6),nullable=True)
    payload:Mapped[dict]=mapped_column(JSON,default=dict)
    drafts:Mapped[list]=mapped_column(JSON,default=list)
    error:Mapped[str]=mapped_column(String(300),default='')
    created_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
    updated_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
class AgentStep(Base):
    __tablename__='agent_steps'
    job_id:Mapped[str]=mapped_column(ForeignKey('agent_jobs.id',ondelete='CASCADE'),primary_key=True)
    key:Mapped[str]=mapped_column(String(160),primary_key=True)
    kind:Mapped[str]=mapped_column(String(16))
    status:Mapped[str]=mapped_column(String(16),default='started')
    request:Mapped[dict]=mapped_column(JSON,default=dict)
    result:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    tool_state:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
class GraphCheckpoint(Base):
    __tablename__='agent_checkpoints'
    job_id:Mapped[str]=mapped_column(ForeignKey('agent_jobs.id',ondelete='CASCADE'),primary_key=True)
    checkpoint_id:Mapped[str]=mapped_column(String(80),primary_key=True)
    data:Mapped[dict]=mapped_column(JSON)
class GraphWrite(Base):
    __tablename__='agent_checkpoint_writes'
    job_id:Mapped[str]=mapped_column(ForeignKey('agent_jobs.id',ondelete='CASCADE'),primary_key=True)
    checkpoint_id:Mapped[str]=mapped_column(String(80),primary_key=True)
    task_id:Mapped[str]=mapped_column(String(80),primary_key=True)
    idx:Mapped[int]=mapped_column(Integer,primary_key=True)
    channel:Mapped[str]=mapped_column(String(200))
    value:Mapped[dict]=mapped_column(JSON)
