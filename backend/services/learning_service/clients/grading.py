"""Best-effort immediate dispatch after the submission transaction commits.

The durable waiting record remains available for explicit retry if dispatch fails.
Do not turn a successful submission into a failed HTTP request when AI is offline.
"""
import httpx
from sqlalchemy import select
from common.config import AI_URL
from ..infrastructure.database import SessionLocal
from ..models import GradeRecord,SubmissionRecord,utcnow
from ..services.grading import public

async def dispatch(cookie,user_id,course_id,submission_id,origin):
    try:
        async with httpx.AsyncClient(timeout=8,trust_env=False) as client:
            response=await client.post(AI_URL+f'/api/ai/courses/{course_id}/submissions/{submission_id}/grade',json={},
                headers={'cookie':cookie,'x-workspace-user':user_id,'origin':origin})
        if response.status_code==200: return
    except httpx.HTTPError: pass
    # Only a never-started job may become dispatch-failed: a lost response can
    # coexist with an already running or completed AI job.
    try:
        with SessionLocal.begin() as db:
            row=db.scalar(select(GradeRecord).where(GradeRecord.submission_id==submission_id).with_for_update())
            untouched=row and (row.input.get('kind')!='assignment' or all(i['status']=='waiting' for i in row.result['items'].values()))
            if row and row.status=='waiting' and untouched:
                row.status='failed';row.error='批改尚未启动，请检查模型设置或服务状态后重试';row.updated_at=utcnow()
                record=db.get(SubmissionRecord,submission_id)
                record.result={**record.result,'aiGrade':public(row)}
    except Exception:
        # The committed waiting record is still the recovery entry point.
        pass
