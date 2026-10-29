import uuid
from typing import Annotated
from fastapi import APIRouter,Depends,File,Form,UploadFile,Request,HTTPException,BackgroundTasks
import secrets
from common import config as internal_config
from sqlalchemy.orm import Session
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import activities as service
from ..schemas.activities import *
router=APIRouter(prefix="/api/courses",tags=["activities"])


@router.post('/{course_id}/activities')
def publish(course_id: uuid.UUID, data: ActivityCreate, request: Request, db: Session=Depends(get_db), user=Depends(workspace_user)):
    if data.source == 'ai':
        key=internal_config.SERVICE_KEY
        if not key or not secrets.compare_digest(request.headers.get('x-service-key',''),key):
            raise HTTPException(403,'AI 来源只能由受信任的服务写入')
    return service.publish(course_id, data, db, user)

@router.post('/{course_id}/activities/{activity_id}/submissions')
def submit(course_id: uuid.UUID, activity_id: uuid.UUID, data: SubmissionInput, request:Request, background_tasks:BackgroundTasks, db: Session=Depends(get_db), user=Depends(workspace_user)):
    result=service.submit(course_id, activity_id, data, db, user)
    grade=result['submission'].get('aiGrade')
    if grade and grade['status']=='waiting':
        from ..clients.grading import dispatch
        background_tasks.add_task(dispatch,request.headers.get('cookie',''),user.id,str(course_id),result['submission']['id'],request.headers.get('origin',''))
    return result

@router.get('/{course_id}/activities/{activity_id}/submissions')
def history(course_id: uuid.UUID, activity_id: uuid.UUID, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.history(course_id, activity_id, db, user)
