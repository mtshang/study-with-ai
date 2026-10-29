import uuid
from fastapi import APIRouter,Depends,Query
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import changes as service
router=APIRouter(prefix="/api/courses",tags=["changes"])
@router.get("/{course_id}/changes")
def changes(course_id:uuid.UUID,after:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=200),db=Depends(get_db),user=Depends(workspace_user)):
    return service.changes_after(db,user,course_id,after,limit)
@router.get("/{course_id}/context")
def context(course_id:uuid.UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return service.current_context(db,user,course_id)
