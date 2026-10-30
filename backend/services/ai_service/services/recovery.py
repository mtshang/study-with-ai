"""Durable in-service scheduling: leases, revocable credentials and step receipts.
Inspired by DeerFlow batch leases and DSH's not-started/outcome-unknown split.
Single AI process remains mandatory; no distributed worker deployment implied.
"""
import asyncio,contextvars,copy,json,uuid,time,logging
from datetime import timedelta
from types import SimpleNamespace
from sqlalchemy import select,or_,func
from fastapi import HTTPException
from ..infrastructure.database import SessionLocal
from ..models import SandboxRun,AgentJob,AgentStep,ChatRun,AssistantTask,CourseAgentState,ToolProposal,utcnow
from ..clients import task_auth
CURRENT=contextvars.ContextVar('agent_job',default=None)
PROCESS=str(uuid.uuid4())
LEASE_SECONDS=30
closing=False
loop_task=None
live={}

def enqueue(db,jid,user,cid,kind,credential,origin,payload=None):
    with db.no_autoflush:row=db.get(AgentJob,jid)
    if row:return row
    row=AgentJob(id=jid,owner_id=user.id,course_id=cid,kind=kind,credential=credential,origin=origin,payload=payload or {})
    db.add(row);return row

class LeaseLost(Exception):pass
class RetryableStep(Exception):pass
class Handle:
    def __init__(self,jid,generation):self.id=jid;self.generation=generation;self.last_draft_save=0
    def guard(self,db):
        row=db.scalar(select(AgentJob).where(AgentJob.id==self.id).with_for_update())
        if not row or row.status!='running' or row.lease_owner!=PROCESS or row.generation!=self.generation or row.lease_until<=utcnow():raise LeaseLost()
        return row
    def check(self):
        with SessionLocal.begin() as db:self.guard(db)
    def capture_draft(self,text):
        if time.monotonic()-self.last_draft_save<.2:return
        with SessionLocal.begin() as db:
            job=self.guard(db);job.payload={**job.payload,'model_draft':text[:24000]}
        self.last_draft_save=time.monotonic()
    def op_id(self,key):return str(uuid.uuid5(uuid.UUID(self.id),key))
    def begin(self,key,kind,request):
        with SessionLocal.begin() as db:
            self.guard(db);row=db.get(AgentStep,(self.id,key))
            if row:
                if row.request!=request or row.kind!=kind:raise HTTPException(409,'恢复步骤与原始请求不匹配')
                return copy.deepcopy(row.result),copy.deepcopy(row.tool_state)
            db.add(AgentStep(job_id=self.id,key=key,kind=kind,request=request))
            return None,{}
    def finish(self,key,result,state=None):
        with SessionLocal.begin() as db:
            job=self.guard(db);row=db.get(AgentStep,(self.id,key))
            if state is not None:job.payload={**job.payload,'tool_state':copy.deepcopy(state)}
            row.result=copy.deepcopy(result);row.tool_state=copy.deepcopy(state or {});row.status='completed'
    def prefix(self,round_number):
        with SessionLocal() as db:
            rows=list(db.scalars(select(AgentStep).where(AgentStep.job_id==self.id,AgentStep.kind=='model',AgentStep.status=='completed')))
            reviews=list(db.scalars(select(AgentStep).where(AgentStep.job_id==self.id,AgentStep.kind=='review',AgentStep.status=='completed')))
        boundary=max((r.request['rounds'] for r in reviews if r.result and not r.result['accepted']),default=0)
        ordered=sorted((r for r in rows if boundary<=int(r.key.split(':')[1])<round_number),key=lambda r:int(r.key.split(':')[1]))
        return ''.join((r.result.get('content') or '')+('\n\n' if r.result.get('tool_calls') and r.result.get('content') else '') for r in ordered)
    async def model(self,number,messages,respond):
        key=f'model:{number}'
        # Messages can be refreshed between a lost refresh checkpoint and replay.
        # A completed response is reused, not matched against refreshed context.
        with SessionLocal.begin() as db:
            self.guard(db);row=db.get(AgentStep,(self.id,key))
            result=copy.deepcopy(row.result) if row else None
            if not row:db.add(AgentStep(job_id=self.id,key=key,kind='model',request={'round':number}))
        if result is not None:return result
        result=await respond(messages,number)
        self.finish(key,result)
        return result

def public(db,jid):
    row=db.get(AgentJob,jid)
    if not row:return None
    return {'status':row.status,'recoveries':row.recoveries,'error':row.error,'interrupted_drafts':row.drafts}

def recover_expired():
    with SessionLocal.begin() as db:
        rows=list(db.scalars(select(AgentJob).where(AgentJob.status=='running',AgentJob.lease_until<utcnow()).with_for_update(skip_locked=True)))
        for row in rows:
            run=db.get(ChatRun,row.id) if row.kind=='teacher' else None
            draft=run.answer if run else row.payload.get('model_draft','')
            if draft:row.drafts=[*row.drafts,{'text':draft,'at':utcnow().isoformat()+'Z'}][-3:]
            state=db.get(CourseAgentState,row.owner_id+':'+row.course_id)
            source=run if row.kind=='teacher' else db.get(AssistantTask,row.id)
            if source and source.status=='completed':
                row.status='completed';row.lease_owner=None;row.lease_until=None
                continue
            if row.kind=='teacher' and state and state.paused:
                row.status='paused'
            elif row.recoveries>=2:
                row.status='needs_attention';row.error='已达到两次自动恢复上限，请明确继续'
            else:
                row.recoveries+=1;row.status='queued';row.error=''
            row.lease_owner=None;row.lease_until=None;row.updated_at=utcnow()
            if row.kind=='sandbox':
                execution=db.get(SandboxRun,row.id)
                if execution and execution.status not in ('completed','runtime_error','timeout'):
                    execution.status='ready' if row.status=='queued' else 'interrupted';execution.error=row.error
            if row.kind=='teacher':
                run=db.get(ChatRun,row.id)
                if run:
                    other=db.scalar(select(ChatRun.id).where(ChatRun.active_key==row.owner_id+':'+row.course_id,ChatRun.id!=row.id))
                    if other:row.status='needs_attention';row.error='已有新的教师回复，请等待后明确继续'
                    run.status='running' if row.status=='queued' else 'interrupted'
                    if row.status=='queued':run.active_key=row.owner_id+':'+row.course_id
                    if row.status!='queued':run.active_key=None
                    run.progress='等待恢复' if row.status=='queued' else '等待手动继续'
            else:
                task=db.get(AssistantTask,row.id)
                if task:task.status='queued' if row.status=='queued' else 'interrupted'
        # A started publishing receipt is not a fresh permission request.
        # Keep the stable operation ID so teaching can return its original result.
        for proposal in db.scalars(select(ToolProposal).where(ToolProposal.status=='executing')):
            parent=db.get(AgentJob,proposal.run_id)
            if parent and parent.status!='running':proposal.status='uncertain'

def claim(jid):
    with SessionLocal.begin() as db:
        row=db.scalar(select(AgentJob).where(AgentJob.id==jid).with_for_update())
        if not row or row.status!='queued':return None
        state=db.get(CourseAgentState,row.owner_id+':'+row.course_id)
        if row.kind=='teacher' and state and state.paused:
            row.status='paused';return None
        row.status='running';row.generation+=1;row.lease_owner=PROCESS
        row.lease_until=utcnow()+timedelta(seconds=LEASE_SECONDS);row.updated_at=utcnow()
        return row.generation

def launch(jid):
    if closing or jid in live:return
    generation=claim(jid)
    if generation is None:return
    from . import runtime,assistants
    with SessionLocal() as db:kind=db.get(AgentJob,jid).kind
    task=asyncio.create_task(run_job(Handle(jid,generation)))
    live[jid]=task
    target=runtime.tasks if kind=='teacher' else assistants.tasks if kind!='sandbox' else {}
    target[jid]=task
    def done(t):
        live.pop(jid,None);target.pop(jid,None)
        if not t.cancelled():t.exception()
    task.add_done_callback(done)

async def heartbeat(handle,parent):
    while True:
        await asyncio.sleep(LEASE_SECONDS/3)
        try:
            with SessionLocal.begin() as db:
                row=handle.guard(db);row.lease_until=utcnow()+timedelta(seconds=LEASE_SECONDS)
        except Exception:
            parent.cancel();return

async def run_job(handle):
    from . import runtime,assistants,configuration,grading
    token=CURRENT.set(handle);heart=asyncio.create_task(heartbeat(handle,asyncio.current_task()))
    interrupted=False;attention=None
    try:
        with SessionLocal() as db:
            row=db.get(AgentJob,handle.id)
            owner,cid,kind,credential,origin,payload=row.owner_id,row.course_id,row.kind,row.credential,row.origin,copy.deepcopy(row.payload)
        user=await task_auth.resolve(credential,owner,cid)
        with SessionLocal() as db:
            source=db.get(ChatRun,handle.id) if kind=='teacher' else db.get(AssistantTask,handle.id)
            already_completed=bool(source and source.status=='completed')
        if already_completed:
            await assistants.wake(user,cid,credential,origin)
            return
        config=None if kind in ('grading','sandbox','rag') else configuration.model_config(user)
        handle.check()
        if kind=='teacher':
            runtime.locks.setdefault(handle.id,asyncio.Lock())
            await runtime.supervise(user,cid,handle.id,credential,origin,config)
        elif kind=='rag':
            from . import rag
            await rag.run_job(user,cid,handle.id,credential,origin)
        elif kind=='sandbox':
            from . import sandbox
            await sandbox.run_job(user,cid,handle.id,credential,origin)
        elif kind=='assistant':
            args=SimpleNamespace(role=payload['role'],task=payload['task'])
            await assistants.execute(user,cid,handle.id,args,credential,origin,config,payload['context'])
        else:
            from ..clients import grading as learning
            source=await learning.call(user,cid,payload['submission_id'],credential,origin)
            with SessionLocal() as db:cached=db.get(AssistantTask,handle.id).payload
            if source['input'].get('kind')=='assignment':
                completed={i['question_id'] for i in source.get('items',[]) if i['status']=='completed'}
                outputs=(cached or {}).get('items',{})
                needs_model=any(q['question_id'] not in completed and q['question_id'] not in outputs for q in source['input']['questions'])
            else:needs_model=not cached and source.get('status')!='completed'
            config=configuration.model_config(user) if needs_model else None
            if source['input'].get('kind')=='assignment':
                from .assignment_grading import execute
            else:execute=grading.execute
            await execute(user,cid,payload['submission_id'],handle.id,source,credential,origin,config,cached)
    except (asyncio.CancelledError,RetryableStep):interrupted=True
    except HTTPException as exc:attention='auth_required' if exc.status_code in (401,403) else 'needs_attention'
    except Exception:attention='needs_attention'
    finally:
        heart.cancel();await asyncio.gather(heart,return_exceptions=True)
        try:
            with SessionLocal.begin() as db:
                row=handle.guard(db)
                state=db.get(CourseAgentState,row.owner_id+':'+row.course_id)
                if closing or interrupted:
                    # Explicit user pause is final for teacher; process exit is resumable.
                    if row.kind=='teacher' and state and state.paused:row.status='paused'
                    else:
                        row.lease_until=utcnow()-timedelta(seconds=1) # next scheduler counts recovery
                elif attention:
                    row.status=attention;row.error='请重新登录后明确继续' if attention=='auth_required' else '恢复准备失败，请检查配置后明确继续'
                else:
                    source=db.get(ChatRun,row.id) if row.kind=='teacher' else db.get(AssistantTask,row.id)
                    row.status='completed' if source and source.status=='completed' else 'paused' if source and source.status=='stopped' else 'needs_attention'
                if row.kind=='sandbox' and not closing and not interrupted and not attention:
                    execution=db.get(SandboxRun,row.id)
                    row.status='completed' if execution and execution.status in ('completed','runtime_error','timeout') else 'needs_attention'
                if row.kind=='rag' and not closing and not interrupted and not attention:
                    row.status='completed' if row.payload.get('rag_ready') else 'needs_attention'
                if row.kind=='sandbox' and row.status in ('needs_attention','auth_required'):
                    execution=db.get(SandboxRun,row.id)
                    if execution and execution.status not in ('completed','runtime_error','timeout'):
                        execution.status='interrupted';execution.error=row.error or '执行需要手动继续'
                if row.status!='running':
                    row.lease_owner=None;row.lease_until=None
                    if row.kind=='teacher':
                        run=db.get(ChatRun,row.id)
                        if run and run.status=='running':
                            run.status='interrupted';run.active_key=None;run.error=row.error
                    else:
                        task=db.get(AssistantTask,row.id)
                        if task and task.status in ('queued','running'):task.status='interrupted'
        except LeaseLost:pass
        CURRENT.reset(token)

async def notify_pending():
    from . import assistants,sandbox_notifications
    # Persistent result inbox is also the notification outbox. No transient-only signal.
    with SessionLocal() as db:
        rows=list(db.scalars(select(AgentJob).join(AssistantTask,AssistantTask.id==AgentJob.id)
            .join(CourseAgentState,(CourseAgentState.owner_id==AgentJob.owner_id)&(CourseAgentState.course_id==AgentJob.course_id))
            .where(AgentJob.status=='completed',AssistantTask.status=='completed',AssistantTask.consumed_by.is_(None),CourseAgentState.paused==False)
            # Filter in SQL before LIMIT: revoked or delayed rows must not starve later results.
            .where(func.coalesce(AgentJob.payload['notification_blocked'].as_boolean(),False)==False,
                   func.coalesce(AgentJob.payload['notify_after'].as_float(),0)<=time.time(),
                   ~select(ChatRun.id).where(ChatRun.active_key==AgentJob.owner_id+':'+AgentJob.course_id).exists())
            .order_by(AgentJob.updated_at).limit(8)))
        candidates=[(j.id,j.owner_id,j.course_id,j.credential,j.origin,copy.deepcopy(j.payload)) for j in rows]
        candidates+=sandbox_notifications.candidates(db)
    for jid,owner,cid,credential,origin,payload in candidates:
        if payload.get('notification_blocked') or payload.get('notify_after',0)>time.time():continue
        with SessionLocal() as db:
            if db.scalar(select(ChatRun.id).where(ChatRun.active_key==owner+':'+cid)):continue
        blocked=False
        try:
            user=await task_auth.resolve(credential,owner,cid)
            await assistants.wake(user,cid,credential,origin,raise_errors=True)
        except HTTPException as exc:blocked=exc.status_code in (401,403)
        except Exception:pass
        with SessionLocal.begin() as db:
            job=db.get(AgentJob,jid)
            if job:
                job.payload={**job.payload,'notification_blocked':blocked,'notify_after':time.time()+15}
                job.updated_at=utcnow()

async def dispatcher():
    while not closing:
        try:
            recover_expired()
            with SessionLocal() as db:
                ids=list(db.scalars(select(AgentJob.id).where(AgentJob.status=='queued').order_by(AgentJob.created_at).limit(8)))
            for jid in ids:
                if len(live)>=8:break
                launch(jid)
            await notify_pending()
        except Exception:
            logging.getLogger(__name__).warning('Agent dispatcher temporarily unavailable; jobs retained')
        await asyncio.sleep(1)

async def startup():
    global closing,loop_task
    closing=False;recover_expired()
    loop_task=asyncio.create_task(dispatcher())
async def shutdown():
    global closing
    closing=True
    if loop_task:loop_task.cancel();await asyncio.gather(loop_task,return_exceptions=True)
    pending=list(live.values())
    for t in pending:t.cancel()
    if pending:await asyncio.gather(*pending,return_exceptions=True)


async def resume(user,jid,cookie,origin):
    from . import assistants
    from ..clients import teaching
    with SessionLocal() as db:
        row=db.get(AgentJob,jid)
        if not row or row.owner_id!=user.id:raise HTTPException(404,'任务不存在')
        cid=row.course_id;kind=row.kind
    if kind=='rag':
        from . import rag
        from ..schemas.rag import IndexRequest
        with SessionLocal() as db:mid=db.get(AgentJob,jid).payload['material_id']
        return await rag.enqueue(user,cid,IndexRequest(id=uuid.uuid4(),material_id=mid),cookie,origin)
    if kind=='sandbox':
        from . import sandbox
        return await sandbox.enqueue(user,cid,jid,cookie,origin)
    await teaching.call(cookie,user.id,cid,origin)
    credential=await task_auth.issue(user,cid,jid,cookie,origin)
    async with assistants.lock(user,cid):
        with SessionLocal.begin() as db:
            row=db.scalar(select(AgentJob).where(AgentJob.id==jid).with_for_update())
            if jid in live or row.status in ('running','queued','completed'):raise HTTPException(409,'当前任务不能重复恢复')
            if kind=='teacher':
                active=db.scalar(select(ChatRun.id).where(ChatRun.active_key==user.id+':'+cid,ChatRun.id!=jid))
                if active:raise HTTPException(409,'请先等待或停止当前教师回复')
                source=db.get(ChatRun,jid);source.status='running';source.active_key=user.id+':'+cid;source.error='';source.progress='准备恢复'
                assistants.state(db,user,cid).paused=False
            else:
                count=len(list(db.scalars(select(AssistantTask.id).where(AssistantTask.owner_id==user.id,AssistantTask.course_id==cid,AssistantTask.status.in_(('queued','running')),AssistantTask.id!=jid).limit(3))))
                if count>=3:raise HTTPException(409,'本课程已有三个助教工作，请稍后继续')
                source=db.get(AssistantTask,jid);source.status='queued';source.error='';source.finished_at=None
                # A result previously consumed as interrupted must be delivered anew.
                source.consumed_by=None
            draft=source.answer if kind=='teacher' else row.payload.get('model_draft','')
            if draft and (not row.drafts or row.drafts[-1]['text']!=draft):
                row.drafts=[*row.drafts,{'text':draft,'at':utcnow().isoformat()+'Z'}][-3:]
            row.credential=credential;row.origin=origin;row.status='queued';row.recoveries=0;row.error=''
            row.lease_owner=None;row.lease_until=None
        launch(jid)
    return {'status':'queued'}


def guard_current(db):
    handle=CURRENT.get()
    if handle:handle.guard(db)
