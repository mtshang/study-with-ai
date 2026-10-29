import uuid
from fastapi import APIRouter,Depends,Request
from sqlalchemy import text,select
from fastapi import HTTPException
from ..models import ChatRun,AssistantTask
from ..services.configuration import model_config
from common.identity import resolve_principal,require_workspace
from ..infrastructure.database import get_db
from ..services.course_tools import CourseReadTools
router=APIRouter()
from .chat import router as chat_router
router.include_router(chat_router)
from .persona import router as persona_router
router.include_router(persona_router)
@router.get("/api/health")
def health(): return {"status":"ok","service":"ai"}
@router.get("/api/ready")
def ready(db=Depends(get_db)):
    db.execute(text("SELECT 1 FROM runtime_schema LIMIT 1"))
    return {"status":"ready","database":"mysql","service":"ai"}
@router.get("/api/ai/status")
def status(user=Depends(resolve_principal),db=Depends(get_db)):
    try:
        model_config(user)
        configured=True
    except HTTPException:
        configured=False
    running=db.scalar(select(ChatRun.id).where(ChatRun.owner_id==user.id,ChatRun.status=='running').limit(1)) is not None
    running=running or db.scalar(select(AssistantTask.id).where(AssistantTask.owner_id==user.id,AssistantTask.status.in_(['queued','running'])).limit(1)) is not None
    return {"model_connected":None,"model_configured":configured,"agents_running":running,"message":"配置不等于连接成功；请在个人 API 设置中测试当前连接"}
@router.get("/api/ai/courses/{course_id}/context")
def context(course_id:uuid.UUID,request:Request,user=Depends(resolve_principal)):
    require_workspace(request,user)
    return CourseReadTools(request.headers.get("cookie",""),user).get_current_course(course_id)

from .extensions import router as extensions_router
router.include_router(extensions_router)

from .sandbox import router as sandbox_router
router.include_router(sandbox_router)
