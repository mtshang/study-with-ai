from uuid import UUID
import secrets
from fastapi import APIRouter,Depends,Request,HTTPException
from common import config
from common.chapter_contract import ChapterCommand
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import chapter_commands as service
router=APIRouter(prefix='/api/courses')

def ai_service(request:Request):
    if not config.SERVICE_KEY or not secrets.compare_digest(request.headers.get('x-service-key',''),config.SERVICE_KEY):
        raise HTTPException(403,'AI章节修改必须经过受信任服务审批流程')

@router.get('/{cid}/outline')
def outline(cid:UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return service.outline(db,user,cid)

@router.get('/{cid}/chapters/{chapter_id}')
def chapter(cid:UUID,chapter_id:UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return service.read_chapter(db,user,cid,chapter_id)

@router.post('/{cid}/chapter-changes/preview',dependencies=[Depends(ai_service)])
def preview(cid:UUID,data:ChapterCommand,db=Depends(get_db),user=Depends(workspace_user)):
    return service.preview(db,user,cid,data)

@router.post('/{cid}/chapter-changes',dependencies=[Depends(ai_service)])
def apply(cid:UUID,data:ChapterCommand,db=Depends(get_db),user=Depends(workspace_user)):
    return service.apply(db,user,cid,data)
