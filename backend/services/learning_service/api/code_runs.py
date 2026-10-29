from uuid import UUID
from fastapi import APIRouter,Depends,Request,BackgroundTasks,HTTPException
from common.execution_contract import ExecutionInput
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import code_runs
router=APIRouter(prefix='/api/courses')
@router.post('/{cid}/activities/{aid}/code-runs')
def start(cid:UUID,aid:UUID,data:ExecutionInput,request:Request,background:BackgroundTasks,db=Depends(get_db),user=Depends(workspace_user)):
    if request.headers.get('x-service-key'):raise HTTPException(403,'代码必须由学生明确运行')
    if data.stdin:raise HTTPException(422,'测试输入必须来自题目快照')
    result,created=code_runs.start(db,user,cid,aid,data)
    if created:background.add_task(code_runs.run,result['id'])
    return result
@router.get('/{cid}/activities/{aid}/code-runs')
def history(cid:UUID,aid:UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return code_runs.history(db,user,cid,aid)

@router.get('/{cid}/code-runs/{sid}')
def evidence(cid:UUID,sid:UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return code_runs.evidence(db,user,cid,sid)
