from sqlalchemy import String,Integer,JSON,Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped,mapped_column
from . import Base,utcnow
class SandboxRun(Base):
    __tablename__='sandbox_runs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    owner_id:Mapped[str]=mapped_column(String(36),index=True)
    course_id:Mapped[str]=mapped_column(String(36),index=True)
    task_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    role:Mapped[str]=mapped_column(String(16))
    title:Mapped[str]=mapped_column(String(120))
    status:Mapped[str]=mapped_column(String(20),default='pending')
    request:Mapped[dict]=mapped_column(JSON)
    sources:Mapped[list]=mapped_column(JSON,default=list)
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    error:Mapped[str]=mapped_column(Text,default='')
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    created_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
