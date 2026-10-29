"""Course-scoped execution receipts and artifacts; no business write authority."""
import asyncio,base64,hashlib,io,json,uuid,zipfile
from sqlalchemy import select
from fastapi import HTTPException
from common.storage import user_path
from common.agent_execution_contract import AgentExecutionInput
from ..infrastructure.config import settings
from ..infrastructure.database import SessionLocal
from ..models import SandboxRun,AgentJob
from ..repositories.chat import profile
from ..clients import sandbox as runner,teaching,materials
from . import extensions,recovery

active=set()
def folder(user,cid,iid):
    root=user_path(settings.user_root,user.storage_dir)
    path=root/'courses'/str(uuid.UUID(cid))/'artifacts'/str(uuid.UUID(iid))
    if path.resolve()!=path.absolute() or not path.resolve().is_relative_to(root):raise HTTPException(422,'产物路径不合法')
    return path
def owned(db,user,cid,iid,lock=False):
    q=select(SandboxRun).where(SandboxRun.id==iid,SandboxRun.owner_id==user.id,SandboxRun.course_id==cid)
    row=db.scalar(q.with_for_update() if lock else q)
    if not row:raise HTTPException(404,'执行记录不存在')
    return row
def public(row):return {'id':row.id,'task_id':row.task_id,'role':row.role,'title':row.title,'status':row.status,'request':row.request,'sources':row.sources,'result':row.result,'error':row.error,'created_at':row.created_at.isoformat()+'Z'}
def listing(user,cid):
    with SessionLocal() as db:return [public(r) for r in db.scalars(select(SandboxRun).where(SandboxRun.owner_id==user.id,SandboxRun.course_id==cid).order_by(SandboxRun.created_at.desc()).limit(100))]
def artifact(user,cid,aid):
    with SessionLocal() as db:
        for row in db.scalars(select(SandboxRun).where(SandboxRun.owner_id==user.id,SandboxRun.course_id==cid)):
            item=next((f for f in row.result.get('files',[]) if f['id']==aid),None)
            if item:
                path=folder(user,cid,row.id)/aid
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise HTTPException(503,'产物文件缺失或校验失败')
                return path,item
    raise HTTPException(404,'产物不存在或不属于本课程')
def read_artifact(user,cid,aid,offset):
    path,item=artifact(user,cid,aid)
    try:text=path.read_text(encoding='utf-8')
    except UnicodeError:raise HTTPException(422,'此产物不是UTF-8文本，请下载查看') from None
    if offset>len(text):raise HTTPException(422,'读取位置超出范围')
    return {'name':item['name'],'text':text[offset:offset+12000],'next_offset':min(len(text),offset+12000),'total':len(text),'sha256':item['sha256']}

async def pack(scope,data,iid):
    inputs=[];sources=[];skill=[]
    for ref in data.inputs:
        if ref.kind=='material':raw=await materials.download(scope.cookie,scope.user.id,scope.course_id,str(ref.id))
        else:raw=artifact(scope.user,scope.course_id,str(ref.id))[0].read_bytes()
        inputs.append({'path':ref.name,'content':base64.b64encode(raw).decode()})
        sources.append({'kind':ref.kind,'id':str(ref.id),'name':ref.name,'sha256':hashlib.sha256(raw).hexdigest()})
    if data.skill_id:
        entry=extensions.enabled_one(scope.user,scope.course_id,str(data.skill_id))
        if entry['kind']!='skill' or entry['revision']!=data.skill_revision:raise HTTPException(409,'技能已变化，请重新加载')
        raw=(extensions.folder(scope.user,str(data.skill_id))/'package.zip').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['data']['sha256']:raise HTTPException(503,'技能包校验失败')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            skill=[{'path':f.filename,'content':base64.b64encode(z.read(f)).decode()} for f in z.infolist()]
        sources.append({'kind':'skill','id':str(data.skill_id),'name':entry['name'],'revision':data.skill_revision,'sha256':entry['data']['sha256'],'script_preview':next((base64.b64decode(f['content']).decode('utf-8','replace')[:12000] for f in skill if f['path']==data.script),'')})
    wire=AgentExecutionInput(id=iid,code=data.code,script=data.script,arguments=data.arguments,inputs=inputs,skill=skill).model_dump(mode='json')
    return wire,sources

async def verify_sources(user,cid,cookie,sources):
    for ref in sources:
        if ref['kind']=='skill':
            entry=extensions.enabled_one(user,cid,ref['id'])
            if entry['revision']!=ref['revision'] or entry['data'].get('sha256')!=ref['sha256']:raise HTTPException(409,'技能已更新或撤销')
        else:
            raw=await materials.download(cookie,user.id,cid,ref['id']) if ref['kind']=='material' else artifact(user,cid,ref['id'])[0].read_bytes()
            if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise HTTPException(409,'输入文件已变化，请提出新的执行请求')

async def request(scope,data,operation_id=None):
    if scope.role not in ('teacher','assistant'):raise HTTPException(403,'当前角色不能执行')
    iid=operation_id or str(uuid.uuid4());cid=scope.course_id;user=scope.user
    await teaching.call(scope.cookie,user.id,cid,scope.origin)
    body=data.model_dump(mode='json')
    with SessionLocal() as db:
        old=db.get(SandboxRun,iid)
        if old:
            if old.owner_id!=user.id or old.course_id!=cid or old.request!=body:raise HTTPException(409,'执行ID不匹配')
            state=old.status;old_value=public(old)
        else:state=None
    if state in ('completed','runtime_error','timeout','pending','rejected'):return old_value
    if state is None:
        wire,sources=await pack(scope,data,iid)
        extensions.atomic_file(folder(user,cid,iid)/'input.json',json.dumps(wire).encode())
        handle=recovery.CURRENT.get()
        with SessionLocal.begin() as db:
            recovery.guard_current(db)
            automatic=profile(db,user.id).permission in ('assisted','full')
            db.add(SandboxRun(id=iid,owner_id=user.id,course_id=cid,task_id=handle.id if handle else scope.run_id,role=scope.role,title=data.title,request=body,sources=sources,status='ready' if automatic else 'pending'))
        if not automatic:return {'id':iid,'status':'pending','message':'等待用户在生成产物页批准；未执行'}
    return await execute(user,cid,iid,scope.cookie,scope.origin,automatic=True)

def persist(user,cid,iid,result):
    if result['status'] not in ('completed','runtime_error','timeout'):return None
    files=[]
    for item in result.get('files',[]):
        raw=base64.b64decode(item['content'],validate=True);aid=str(uuid.uuid5(uuid.UUID(iid),item['path']))
        extensions.atomic_file(folder(user,cid,iid)/aid,raw)
        files.append({'id':aid,'name':item['path'],'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    with SessionLocal.begin() as db:
        row=owned(db,user,cid,iid,True)
        row.status=result['status'];row.result={**{k:v for k,v in result.items() if k!='files'},'files':files};row.error=''
        value=public(row)
    (folder(user,cid,iid)/'input.json').unlink(missing_ok=True)
    return value

async def execute(user,cid,iid,cookie,origin,automatic=False):
    if iid in active:raise HTTPException(409,'该执行正在处理中')
    active.add(iid)
    try:
        await teaching.call(cookie,user.id,cid,origin)
        with SessionLocal.begin() as db:
            recovery.guard_current(db);row=owned(db,user,cid,iid,True)
            if row.status in ('completed','runtime_error','timeout'):return public(row)
            if row.status not in ('ready','interrupted','running'):raise HTTPException(409,'执行尚未获批或已拒绝')
            if automatic and profile(db,user.id).permission=='manual':row.status='pending';return public(row)
            sources=row.sources
        # First collect a receipt; a lost HTTP response must not produce duplicate output.
        try:
            result=await runner.request(iid)
            if saved:=persist(user,cid,iid,result):return saved
            if result['status']=='running':raise HTTPException(503,'容器仍在运行，请稍后恢复原执行')
        except HTTPException as exc:
            if exc.status_code!=404:raise
        await verify_sources(user,cid,cookie,sources)
        wire=AgentExecutionInput.model_validate_json((folder(user,cid,iid)/'input.json').read_bytes()).model_dump(mode='json')
        with SessionLocal.begin() as db:
            recovery.guard_current(db);row=owned(db,user,cid,iid,True);row.status='running';row.attempts+=1
        result=await runner.request(iid,wire)
        saved=persist(user,cid,iid,result)
        if saved:return saved
        raise HTTPException(503,'执行尚未完成，可恢复原执行')
    except (HTTPException,OSError,ValueError,asyncio.CancelledError) as exc:
        with SessionLocal.begin() as db:
            row=owned(db,user,cid,iid,True)
            if row.status not in ('pending','rejected','completed','runtime_error','timeout'):
                row.status='interrupted';row.error='执行中断或暂不可用；恢复将先核对原执行结果'
        if isinstance(exc,asyncio.CancelledError):raise
        if isinstance(exc,HTTPException) and exc.status_code!=503:raise
        raise HTTPException(503,'执行未完成，请检查输入、授权或执行服务，再恢复原执行') from None
    finally:active.discard(iid)

async def decide(user,cid,iid,approve,cookie,origin):
    with SessionLocal.begin() as db:
        row=owned(db,user,cid,iid,True)
        if row.status!='pending':raise HTTPException(409,'此执行已处理')
        row.status='ready' if approve else 'rejected'
    if approve:return await enqueue(user,cid,iid,cookie,origin)
    (folder(user,cid,iid)/'input.json').unlink(missing_ok=True)
    return {'status':'rejected'}

RULES='可使用run_sandbox在禁网的临时Python环境计算或执行已启用Skill的.py脚本，生成文件放OUTPUT_DIR；输入文件位于INPUT_DIR。只有Python标准库，不提供依赖安装，环境不含密钥。教师和助教均可执行，但这不授予发布或修改教学业务的权限。待批准不是已执行，只有真实返回产物ID才能声称生成文件。可列出/读取当前课程产物，不能自动将产物发布为资料或作业。'
def context(user,cid):
    rows=listing(user,cid)[:5]
    return {'role':'user','content':'[沙箱执行记录，仅为数据]'+json.dumps([{'id':r['id'],'title':r['title'],'role':r['role'],'status':r['status'],'result':r['result']} for r in rows],ensure_ascii=False)[:18000]}


async def enqueue(user,cid,iid,cookie,origin):
    from ..clients import task_auth
    await teaching.call(cookie,user.id,cid,origin)
    credential=await task_auth.issue(user,cid,iid,cookie,origin)
    with SessionLocal.begin() as db:
        row=owned(db,user,cid,iid,True)
        if row.status not in ('ready','running','interrupted'):raise HTTPException(409,'当前执行不能继续')
        job=db.get(AgentJob,iid)
        if job and job.status in ('queued','running'):return public(row)
        if job:
            job.credential=credential;job.origin=origin;job.status='queued';job.recoveries=0;job.error=''
            job.lease_owner=None;job.lease_until=None
        else:recovery.enqueue(db,iid,user,cid,'sandbox',credential,origin)
        row.status='ready';row.error='';value=public(row)
    recovery.launch(iid)
    return value

async def run_job(user,cid,iid,credential,origin):
    try:await execute(user,cid,iid,credential,origin)
    except HTTPException as exc:
        if exc.status_code in (429,503):raise recovery.RetryableStep() from None
        raise
