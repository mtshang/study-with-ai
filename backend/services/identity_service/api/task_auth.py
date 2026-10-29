import uuid
from fastapi import APIRouter,Request,Depends,HTTPException
from common.task_auth import encode,decode,require_service
from ..infrastructure.database import get_db
from ..infrastructure.security import COOKIE,digest
from ..repositories.accounts import session_user
from .accounts import current_user
router=APIRouter(prefix='/api/internal',dependencies=[Depends(require_service)])
@router.post('/task-grants/{course_id}/{task_id}')
def issue(course_id:uuid.UUID,task_id:uuid.UUID,request:Request,user=Depends(current_user)):
    return {'grant':encode({'v':1,'session':digest(request.cookies[COOKIE]),'owner':user.id,'course':str(course_id),'task':str(task_id)})}
@router.get('/task-principal')
def principal(request:Request,db=Depends(get_db)):
    claims=decode(request.headers.get('x-task-grant',''))
    user=session_user(db,claims['session'])
    if not user or user.id!=claims['owner']:raise HTTPException(401,'原登录会话已失效，请重新登录后明确继续任务')
    return {'id':user.id,'username':user.username,'storage_dir':user.storage_dir,'course_id':claims['course'],'task_id':claims['task']}
