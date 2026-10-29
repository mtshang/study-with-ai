import uuid
from typing import Annotated
from fastapi import APIRouter,Depends,File,Form,UploadFile
from sqlalchemy.orm import Session
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import courses as service
from ..schemas.courses import *
router=APIRouter(prefix="/api/courses",tags=["courses"])


@router.get('')
def list_courses(db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.list_courses(db, user)

@router.get('/{course_id}')
def get_course(course_id: uuid.UUID, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.get_course(course_id, db, user)

@router.post('', status_code=201)
def create_course(data: CourseCreate, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.create_course(data, db, user)

@router.put('/{course_id}')
def update_course(course_id: uuid.UUID, data: CourseUpdate, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.update_course(course_id, data, db, user)

@router.get('/{course_id}/revisions/{version}')
def revision(course_id: uuid.UUID, version: int, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.revision(course_id, version, db, user)
