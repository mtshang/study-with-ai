from contextlib import asynccontextmanager
import secrets,threading
from fastapi import FastAPI,Depends,Header,HTTPException
from common.body_limit import BodyLimitMiddleware
from common.execution_contract import ExecutionInput,ExecutionResult
from . import config,runner

slots=threading.BoundedSemaphore(2)
def authorize(x_runner_key:str=Header(default='')):
    if not config.KEY or not secrets.compare_digest(x_runner_key,config.KEY):raise HTTPException(403,'执行服务凭证无效')

@asynccontextmanager
async def lifespan(app):
    if not runner.recover(): runner.cleanup_failed.set()
    yield

app=FastAPI(title='Study with AI — Python execution',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)
@app.get('/internal/ready',dependencies=[Depends(authorize)])
def ready():
    if not runner.ready():raise HTTPException(503,'Python镜像或Docker未就绪')
    return {'status':'ready'}
@app.post('/internal/execute',response_model=ExecutionResult,dependencies=[Depends(authorize)])
def execute(data:ExecutionInput):
    if not slots.acquire(blocking=False):raise HTTPException(429,'代码执行槽已满，请稍后新建运行')
    try:return runner.execute(data)
    finally:slots.release()

from uuid import UUID
from common.agent_execution_contract import AgentExecutionInput,AgentExecutionResult
from . import agent_runner
@app.post('/internal/agent-executions',response_model=AgentExecutionResult,dependencies=[Depends(authorize)])
def agent_execute(data:AgentExecutionInput):
    if not slots.acquire(blocking=False):raise HTTPException(429,'执行槽已满')
    try:return agent_runner.execute(data)
    finally:slots.release()
@app.get('/internal/agent-executions/{iid}',response_model=AgentExecutionResult,dependencies=[Depends(authorize)])
def agent_status(iid:UUID):return agent_runner.status(str(iid))

