from sqlalchemy import String,JSON,ForeignKey
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped,mapped_column
from . import Base,utcnow

class GradeRecord(Base):
    __tablename__='submission_grades'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    submission_id:Mapped[str]=mapped_column(ForeignKey('submissions.id',ondelete='CASCADE'),unique=True)
    input_hash:Mapped[str]=mapped_column(String(64))
    input:Mapped[dict]=mapped_column(JSON)
    status:Mapped[str]=mapped_column(String(24),default='waiting')
    result:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    model:Mapped[str]=mapped_column(String(120),default='')
    error:Mapped[str]=mapped_column(String(300),default='')
    created_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
    updated_at:Mapped[object]=mapped_column(DATETIME(fsp=6),default=utcnow)
