"""Audited external effects. Unknown outcomes are never automatically resent."""
import asyncio
import json
import uuid
from sqlalchemy import select
from fastapi import HTTPException
from jsonschema import Draft202012Validator, ValidationError
from ..models import MCPInvocation, Extension, ToolProposal, ChatRun
from ..infrastructure.database import SessionLocal
from ..repositories.chat import profile
from ..clients import mcp_http
from . import extensions, recovery

slots = asyncio.Semaphore(4)
active_calls = set()


def definition(user, cid, eid, name, expected, effect):
    entry = extensions.enabled_one(user, cid, eid)
    if entry['kind'] != 'mcp' or entry['revision'] != expected:
        raise HTTPException(409, 'MCP配置或权限已变化，请重新列出工具')
    tool = next((t for t in entry['data'].get('tools', []) if t['name'] == name), None)
    if not tool or tool['effect'] != effect:
        raise HTTPException(403, '该工具未启用或不具备所要求的用途授权')
    return tool


def tools_for(user, cid, role):
    entries = extensions.enabled(user, cid, 'mcp')
    result = [{'extension_id':e['id'], 'name':e['name'], 'revision':e['revision'],
             'tools':[t for t in e['data'].get('tools', []) if t['effect'] == 'read' or (role == 'teacher' and t['effect'] == 'write')]}
            for e in entries]
    if len(json.dumps(result,ensure_ascii=False))>60000:
        raise HTTPException(422,'已启用工具定义过多，请减少本课程连接器或禁用暂不用的工具')
    return result


def public(row):
    return {'id':row.id, 'extension_id':row.extension_id, 'tool':row.tool,
            'effect':row.effect, 'arguments':row.arguments, 'status':row.status,
            'result':row.result, 'error':row.error}


def history(user, cid):
    with SessionLocal() as db:
        return [public(r) for r in db.scalars(select(MCPInvocation).where(MCPInvocation.owner_id == user.id, MCPInvocation.course_id == cid).order_by(MCPInvocation.created_at.desc()).limit(30))]


async def request(scope, data, effect, operation_id=None):
    user, cid = scope.user, scope.course_id
    if effect == 'write' and scope.role != 'teacher':
        raise HTTPException(403, '助教不能调用有副作用的MCP工具')
    tool = definition(user,cid,str(data.extension_id),data.tool,data.revision,effect)
    encoded = json.dumps(data.arguments, ensure_ascii=False)
    if len(encoded) > 16000:
        raise HTTPException(422, 'MCP参数最多16000字符')
    try:
        Draft202012Validator(tool['inputSchema']).validate(data.arguments)
    except ValidationError:
        raise HTTPException(422, 'MCP参数不符合该工具声明') from None
    iid = operation_id or str(uuid.uuid4())
    handle = recovery.CURRENT.get()
    with SessionLocal.begin() as db:
        recovery.guard_current(db)
        old = db.get(MCPInvocation, iid)
        if old:
            if (old.owner_id,old.course_id,old.extension_id,old.tool,old.arguments,old.effect) != (user.id,cid,str(data.extension_id),data.tool,data.arguments,effect):
                raise HTTPException(409, '调用标识已用于其他请求')
            if old.status == 'completed':
                return {'call_id':iid, 'status':'completed', 'result':old.result}
            if old.status == 'pending':
                return {'call_id':iid, 'status':'pending_approval'}
            raise HTTPException(409, '原MCP调用结果未知或已经处理；不会自动重复调用，请查看调用记录')
        if effect == 'write':
            unknown = db.scalar(select(MCPInvocation.id).where(MCPInvocation.owner_id==user.id,MCPInvocation.course_id==cid,MCPInvocation.effect=='write',MCPInvocation.status.in_(('executing','uncertain'))).limit(1))
            if unknown:
                raise HTTPException(409, '本课程有外部操作结果尚未核实，请用户先核实调用记录')
        automatic = effect == 'read' or profile(db,user.id).permission == 'full'
        row = MCPInvocation(id=iid,owner_id=user.id,course_id=cid,job_id=handle.id if handle else scope.run_id,
                            extension_id=str(data.extension_id),extension_revision=data.revision,
                            tool=data.tool,effect=effect,arguments=data.arguments,status='ready' if automatic else 'pending')
        db.add(row)
        if effect == 'write':
            if not scope.run_id:
                raise HTTPException(403, '只有教师任务可以请求外部写操作')
            db.add(ToolProposal(id=iid,run_id=scope.run_id,status='pending',payload={
                'kind':'mcp','title':'MCP：'+data.tool,'description':'外部操作可能改变远端数据。',
                'arguments':data.arguments,'call_id':iid,'_automatic_authorized':automatic}))
    if not automatic:
        return {'call_id':iid,'status':'pending_approval','message':'等待用户批准，尚未执行'}
    return await execute(user,iid)


async def execute(user, iid):
    async with slots:
        with SessionLocal.begin() as db:
            recovery.guard_current(db)
            row=db.scalar(select(MCPInvocation).where(MCPInvocation.id==iid).with_for_update())
            if not row or row.owner_id!=user.id:
                raise HTTPException(404,'调用不存在')
            if row.status=='completed':
                return {'call_id':iid,'status':'completed','result':row.result}
            if row.status!='ready':
                raise HTTPException(409,'此调用不能重复执行；结果未知时必须人工核实')
            tool=definition(user,row.course_id,row.extension_id,row.tool,row.extension_revision,row.effect)
            ext=extensions.owned(db,user,row.extension_id)
            url,headers=ext.data['url'],extensions.connector_headers(user,ext)
            args=row.arguments
            cid,eid,tool_name,version,effect=row.course_id,row.extension_id,row.tool,row.extension_revision,row.effect
            row.status='executing'
            proposal=db.get(ToolProposal,iid)
            if proposal:proposal.status='executing'
        def before_call():
            # Discovery yields to other requests. Re-check revocation immediately before dispatch.
            definition(user,cid,eid,tool_name,version,effect)
            with SessionLocal.begin() as db:
                recovery.guard_current(db)
                proposal=db.get(ToolProposal,iid)
                if effect=='write' and proposal and proposal.payload.get('_automatic_authorized') and profile(db,user.id).permission!='full':
                    raise HTTPException(409,'自动执行权限已变化，请重新确认')
        active_calls.add(iid)
        try:
            result=await mcp_http.invoke(url,headers,tool,args,before_call=before_call)
        except BaseException as exc:
            # Cancellation and a lost response are not evidence that the server did nothing.
            with SessionLocal.begin() as db:
                row=db.get(MCPInvocation,iid)
                row.status='uncertain';row.error='外部调用结果未知，请核实远端状态；系统不会自动重发'
                proposal=db.get(ToolProposal,iid)
                if proposal:proposal.status='uncertain';proposal.error=row.error
            if isinstance(exc,asyncio.CancelledError):raise
            if not isinstance(exc,Exception):raise
            return {'call_id':iid,'status':'uncertain','message':'外部结果未知，需用户核实'}
        finally:
            active_calls.discard(iid)
        with SessionLocal.begin() as db:
            row=db.get(MCPInvocation,iid);row.status='completed';row.result=result;row.error=''
            proposal=db.get(ToolProposal,iid)
            if proposal:
                proposal.status='published';proposal.payload={**proposal.payload,'result':result}
        return {'call_id':iid,'status':'completed','result':result}


async def decide(user,iid,approve):
    with SessionLocal.begin() as db:
        row=db.scalar(select(MCPInvocation).where(MCPInvocation.id==iid,MCPInvocation.owner_id==user.id).with_for_update())
        if not row:raise HTTPException(404,'调用不存在')
        if row.status!='pending':raise HTTPException(409,'调用已处理，不能重复批准或重发')
        row.status='ready' if approve else 'rejected'
        proposal=db.get(ToolProposal,iid)
        if not approve and proposal:proposal.status='rejected'
    return await execute(user,iid) if approve else {'status':'rejected'}


def review_outcome(user,cid,iid,note):
    with SessionLocal.begin() as db:
        row=db.scalar(select(MCPInvocation).where(MCPInvocation.id==iid,MCPInvocation.owner_id==user.id,MCPInvocation.course_id==cid).with_for_update())
        if not row:raise HTTPException(404,'调用不存在')
        if row.status not in ('uncertain','executing','ready'):
            raise HTTPException(409,'只需核实尚不明确的调用')
        if iid in active_calls or row.job_id in recovery.live:
            raise HTTPException(409,'任务仍在运行，请等待或停止后核实')
        row.status='reviewed';row.result={'user_review':note.strip()};row.error=''
        proposal=db.get(ToolProposal,iid)
        if proposal:proposal.status='reviewed';proposal.error='';proposal.payload={**proposal.payload,'result':row.result}
        return public(row)
