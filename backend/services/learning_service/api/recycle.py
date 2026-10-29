from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Request,HTTPException
from common.recycle_contract import RecycleCommand
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from .chapter_commands import ai_service
from ..services import recycle
router=APIRouter(prefix='/api/courses')
@router.get('/{cid}/trash/{kind}')
def listing(cid:UUID,kind:Literal['chapter','exercise','assignment'],db=Depends(get_db),user=Depends(workspace_user)):
    return recycle.listing(db,user,cid,kind)
@router.get('/{cid}/teaching-activities')
def catalog(cid:UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return recycle.activity_catalog(db,user,cid)
@router.post('/{cid}/trash-actions')
def apply(cid:UUID,data:RecycleCommand,request:Request,db=Depends(get_db),user=Depends(workspace_user)):
    if request.headers.get('x-service-key'): raise HTTPException(403,'服务不能代替用户永久删除')
    return recycle.apply(db,user,cid,data,'user')
@router.post('/{cid}/ai-trash-preview',dependencies=[Depends(ai_service)])
def preview(cid:UUID,data:RecycleCommand,db=Depends(get_db),user=Depends(workspace_user)):
    return recycle.preview(db,user,cid,data)
@router.post('/{cid}/ai-trash-actions',dependencies=[Depends(ai_service)])
def ai_apply(cid:UUID,data:RecycleCommand,db=Depends(get_db),user=Depends(workspace_user)):
    return recycle.apply(db,user,cid,data,'ai')
