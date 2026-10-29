"""Global defaults are versioned; courses inherit by authoritative creation time."""
from datetime import datetime, timezone
from sqlalchemy import select
from fastapi import HTTPException
from ..models import PersonaDefault, CoursePersona
from ..repositories.chat import profile
from ..infrastructure.database import SessionLocal

DEFAULT='你是一位耐心的教学导师。用清楚的例子解释知识，根据学生反馈调整节奏。'

def global_view(db,owner):
    row=db.scalar(select(PersonaDefault).where(PersonaDefault.owner_id==owner).order_by(PersonaDefault.revision.desc()).limit(1))
    return {'version':row.revision if row else 0,'prompt':row.prompt if row else DEFAULT}

def save_default(owner,data):
    with SessionLocal.begin() as db:
        profile(db,owner)
        current=global_view(db,owner)
        if current['version']!=data.version:raise HTTPException(409,'人格设置已变化，请重新读取')
        if current['prompt']==data.prompt:return current
        db.add(PersonaDefault(owner_id=owner,revision=data.version+1,prompt=data.prompt))
        return {'version':data.version+1,'prompt':data.prompt}

def course_row(db,owner,cid,context):
    # Caller holds profile lock, serializing lazy initialization and global edits.
    row=db.get(CoursePersona,(owner,cid))
    if row:return row
    historical=None
    if context.get('course_created_at'):
        timestamp=datetime.fromisoformat(context['course_created_at']).astimezone(timezone.utc).replace(tzinfo=None)
        historical=db.scalar(select(PersonaDefault).where(PersonaDefault.owner_id==owner,PersonaDefault.created_at<=timestamp).order_by(PersonaDefault.revision.desc()).limit(1))
    row=CoursePersona(owner_id=owner,course_id=cid,prompt=historical.prompt if historical else DEFAULT,source_revision=historical.revision if historical else 0,version=1)
    db.add(row);db.flush();return row

def course_view(owner,cid,context,data=None):
    with SessionLocal.begin() as db:
        profile(db,owner)
        row=course_row(db,owner,cid,context)
        if data:
            if row.version!=data.version:raise HTTPException(409,'课程人格已变化，请重新读取')
            if row.prompt!=data.prompt:
                row.prompt=data.prompt;row.version+=1;row.source_revision=-1
        return {'version':row.version,'prompt':row.prompt,'source_revision':row.source_revision}
