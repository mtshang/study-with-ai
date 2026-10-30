"""Per-run course tools. Capability checks precede argument parsing and effects.

User/course/session are bound by the server, not exposed in tool schemas.
Reading evidence and limits belong to this execution, never a global agent.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError

from ..clients import teaching, chapters, materials
from ..infrastructure.database import SessionLocal
from ..models import ToolProposal, utcnow
from ..repositories import chat as repository
from . import reading_skills, learning_context, memory
from .tool_registry import Role, authorize, schemas_for


@dataclass(frozen=True)
class ToolScope:
    user: Any = field(repr=False)
    course_id: str
    role: Role
    cookie: str = field(repr=False)
    origin: str = field(repr=False)
    run_id: str | None = None
    allow_delegate: bool = False

    def __post_init__(self):
        if self.role not in ('teacher', 'assistant', 'grader'):
            raise ValueError('Unknown server execution role')
        if self.role != 'teacher' and self.allow_delegate:
            raise ValueError('Only a teacher may delegate')


class CourseToolSession:
    def __init__(self, scope: ToolScope, *, publish=None, delegate=None, run_lock=None):
        self.scope = scope
        self._publish = publish
        self._delegate = delegate
        self._run_lock = run_lock
        self.observations = {}
        self.context = None
        self.have_read = False
        self.created = 0
        self.loaded_skills = set()
        self.available_materials = {}
        self.outline_version = None
        self.read_chapters = {}
        self.chapter_edits = 0
        self.activity_catalog = None
        self.recycle_count = 0
        from .recovery import CURRENT
        from ..models import AgentJob
        handle=CURRENT.get()
        if handle:
            with SessionLocal() as db:
                job=db.get(AgentJob,handle.id)
                if job:self.restore_state(job.payload.get('tool_state',{}))

    def schemas(self):
        return schemas_for(self.scope.role, allow_delegate=self.scope.allow_delegate)

    def invalidate_business_reads(self):
        self.observations = {}
        self.have_read = False
        self.outline_version = None
        self.read_chapters = {}
        self.activity_catalog = None

    async def _execute(self, call):
        # Malformed envelopes cannot safely form tool-result messages. Fail the
        # run before any side effect instead of guessing a provider call ID.
        if not isinstance(call, dict) or not isinstance(call.get('id'), str) or not call['id']:
            raise HTTPException(502, '模型工具请求缺少有效标识')
        try:
            fn = call['function']
            if not isinstance(fn, dict) or not isinstance(fn.get('name'), str):
                raise ValueError('Invalid function')
            spec = authorize(fn['name'], self.scope.role, allow_delegate=self.scope.allow_delegate)
            raw = fn['arguments']
            if not isinstance(raw, str) or len(raw) > 20000:
                raise ValueError('Invalid arguments')
            args = json.loads(raw)
            if not isinstance(args, dict):
                raise ValueError('Arguments must be an object')
            data = spec.args_model.model_validate(args)
            recovered=None
            op_id=getattr(self,'operation_id',None)
            if op_id and spec.effect!='read':
                with SessionLocal() as db:
                    old=db.get(ToolProposal,op_id)
                    if old and old.run_id==self.scope.run_id and old.payload.get('kind') not in ('memory','mcp'):
                        recovered=old.status
                        auto_authorized=old.payload.get('_automatic_authorized',False)
                if recovered=='published':result={'status':'published','activity_id':op_id}
                elif recovered in ('executing','uncertain'):
                    if recovered=='executing':
                        with SessionLocal.begin() as db:db.get(ToolProposal,op_id).status='uncertain'
                    result=await self._publish(op_id)
                elif recovered=='pending':
                    with SessionLocal() as db:current_permission=repository.profile(db,self.scope.user.id).permission
                    if auto_authorized and current_permission in ('assisted','full'):result=await self._publish(op_id)
                    else:result={'status':'pending_approval','proposal_id':op_id,'message':'原方案仍等待批准。'}
                elif recovered:result={'error':'原操作未完成，请核对当前状态后提出新方案'}
                else:result=await getattr(self,spec.handler)(data,spec.name)
            else:result=await getattr(self,spec.handler)(data,spec.name)
            if spec.effect == 'read' and spec.name != 'read_course_memory':
                self.observations[call['id']] = {'text':json.dumps(result, ensure_ascii=False),'tool':spec.name,'arguments':data.model_dump(mode='json'),'observed_at':utcnow().isoformat()+'Z'}
        except (ValueError, ValidationError, TypeError, KeyError):
            result = {'error': '工具参数格式不正确，请按定义重新填写'}
        except HTTPException as exc:
            result = {'error': exc.detail}
        return {'role': 'tool', 'tool_call_id': call['id'],
                'content': json.dumps(result, ensure_ascii=False)}

    def export_state(self):
        return {k:getattr(self,k) for k in ('observations','context','have_read','created','available_materials','outline_version','read_chapters','chapter_edits','activity_catalog','recycle_count')} | {'loaded_skills':sorted(self.loaded_skills)}

    def restore_state(self,state):
        for key,value in state.items():
            if key=='loaded_skills':self.loaded_skills=set(value)
            elif key in ('observations','context','have_read','created','available_materials','outline_version','read_chapters','chapter_edits','activity_catalog','recycle_count'):
                setattr(self,key,value)

    async def execute(self,call):
        from .recovery import CURRENT
        handle=CURRENT.get()
        if not handle:return await self._execute(call)
        handle.check()
        # Validate envelope through the ordinary path before creating any receipt.
        if not isinstance(call,dict) or not isinstance(call.get('id'),str):return await self._execute(call)
        key='tool:'+str(handle.round_number)+':'+call['id']
        if len(key)>160:raise HTTPException(502,'工具标识过长')
        from ..models import AgentStep
        from .tool_registry import REPLAYABLE_WRITES
        with SessionLocal() as db:was_started=db.get(AgentStep,(handle.id,key)) is not None
        result,state=handle.begin(key,'tool',call)
        if result is not None:
            self.restore_state(state)
            return result
        if was_started:
            spec=authorize(call['function']['name'],self.scope.role,allow_delegate=self.scope.allow_delegate)
            if spec.effect!='read' and spec.name not in REPLAYABLE_WRITES:
                raise HTTPException(409,'工具结果未知，未配置核对机制，需人工处理')
        self.operation_id=handle.op_id(key)
        try:
            result=await self._execute(call)
            with SessionLocal() as db:
                proposal=db.get(ToolProposal,self.operation_id)
                uncertain=bool(proposal and proposal.payload.get('kind')!='mcp' and proposal.status in ('uncertain','executing'))
            if uncertain:
                from .recovery import RetryableStep
                raise RetryableStep()
            handle.finish(key,result,self.export_state())
            return result
        finally:self.operation_id=None

    async def execute_batch(self, calls):
        if not isinstance(calls, list) or not 1 <= len(calls) <= 4:
            raise HTTPException(502, '单轮工具请求数量不合法')
        # Validate IDs before the first side effect, including duplicates.
        ids = [c.get('id') if isinstance(c, dict) else None for c in calls]
        if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            raise HTTPException(502, '模型工具请求标识缺失或重复')
        return [await self.execute(call) for call in calls]

    async def _chapter_call(self, action, payload=None, chapter_id=None):
        s = self.scope
        return await chapters.call(s.cookie, s.user.id, s.course_id, s.origin,
                                   action, payload, chapter_id=chapter_id)

    async def get_current_course(self, data, name):
        s = self.scope
        self.context = await teaching.call(s.cookie, s.user.id, s.course_id, s.origin)
        self.have_read = True
        return learning_context.course_overview(self.context)

    async def get_course_outline(self, data, name):
        result = await self._chapter_call('outline')
        self.outline_version = result['course_version']
        self.read_chapters = {}
        return result

    async def read_chapter(self, data, name):
        result = await self._chapter_call('read', chapter_id=str(data.chapter_id))
        self.read_chapters[str(data.chapter_id)] = result['course_version']
        return result

    async def list_teaching_activities(self, data, name):
        self.activity_catalog = await self._chapter_call('activities')
        return self.activity_catalog

    async def read_code_submission(self, data, name):
        return await self._chapter_call('code-result', chapter_id=str(data.submission_id))

    async def search_course_knowledge(self,data,name):
        from . import rag
        s=self.scope
        return await rag.search(s.user,s.course_id,s.cookie,data)

    async def list_course_materials(self, data, name):
        s = self.scope
        rows = await materials.call(s.cookie, s.user.id, s.course_id)
        self.available_materials = {r['id']: r for r in rows}
        return rows

    async def load_reading_skill(self, data, name):
        result = reading_skills.load(data.skill_id)
        self.loaded_skills.add(data.skill_id)
        return result

    async def read_course_material(self, data, name):
        mid = str(data.material_id)
        entry = self.available_materials.get(mid)
        if not entry:
            raise HTTPException(409, '请先列出本课程资料，使用真实资料标识')
        if not entry['readable']:
            raise HTTPException(422, '当前无法读取此格式或链接')
        if entry.get('skill_id') and entry['skill_id'] not in self.loaded_skills:
            raise HTTPException(409, '请先加载该资料对应的内置读取技能')
        s = self.scope
        return await materials.call(s.cookie, s.user.id, s.course_id, mid, {
            'offset': data.offset,
            **({'source_sha256': data.source_sha256} if data.source_sha256 else {}),
        })

    async def read_course_memory(self, data, name):
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return memory.internal_view(s.user.id,s.course_id)

    async def manage_course_memory(self, data, name):
        s=self.scope
        context=await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        owned={c['id'] for c in context['course'].get('chapters',[])}
        if any(str(cid) not in owned for cid in data.affected_chapters):
            raise HTTPException(422,'冲突范围必须使用本课程真实章节')
        return memory.propose(s,data,self.observations,operation_id=getattr(self,'operation_id',None))

    async def _propose(self, proposal_id, payload):
        s = self.scope
        # Defense in depth: even an accidental internal write-handler call by
        # an assistant cannot create a pending proposal or acquire authority.
        if s.role != 'teacher' or not s.run_id or self._publish is None or self._run_lock is None:
            raise HTTPException(403, '当前执行角色不能提交业务修改')
        with SessionLocal.begin() as db:
            from .recovery import guard_current
            guard_current(db)
            memory.check_gate(db,s.user.id,s.course_id,payload)
            permission = repository.profile(db, s.user.id).permission
            db.add(ToolProposal(id=proposal_id,run_id=s.run_id,payload={**payload,'_automatic_authorized':permission in ('assisted','full')}))
        async with self._run_lock:
            if permission in ('assisted', 'full'):
                return await self._publish(proposal_id)
            return {'status': 'pending_approval', 'proposal_id': proposal_id,
                    'message': '方案已保存，等待用户批准；尚未执行。'}

    async def publish_activity(self, data, name):
        if not self.have_read:
            raise HTTPException(409, '请先调用 get_current_course 读取当前课程')
        if self.created >= 2:
            raise HTTPException(422, '本轮最多发布或提议两项练习或作业')
        proposal_id = getattr(self,'operation_id',None) or str(uuid.uuid4())
        if name == 'publish_python_exercise':
            questions = [{'prompt': data.prompt, 'python': data.python.model_dump(), 'explanation': ''}]
        elif name == 'publish_exercise':
            questions = [{'prompt': data.prompt, 'options': data.options,
                          'correct': data.correct, 'explanation': data.explanation}]
        else:
            questions = [q.model_dump() for q in data.questions]
        payload = {'id': proposal_id, 'kind': 'assignment' if name == 'publish_assignment' else 'exercise',
                   'title': data.title, 'description': getattr(data, 'description', ''),
                   'chapter_id': str(data.chapter_id) if data.chapter_id else None,
                   'questions': questions, 'source': 'ai', 'expected_version': self.context['course_version']}
        self.created += 1
        return await self._propose(proposal_id, payload)

    async def edit_course_chapters(self, data, name):
        if self.outline_version is None:
            raise HTTPException(409, '请先读取最新完整章节目录')
        if self.chapter_edits >= 2:
            raise HTTPException(422, '本轮最多提交两份章节方案')
        for op in data.operations:
            if op.action == 'update' and self.read_chapters.get(str(op.chapter_id)) != self.outline_version:
                raise HTTPException(409, '修改章节内容前，请读取同版本的完整正文')
        proposal_id = getattr(self,'operation_id',None) or str(uuid.uuid4())
        command = {'id': proposal_id, 'expected_version': self.outline_version,
                   **data.model_dump(mode='json', exclude_unset=True)}
        preview = await self._chapter_call('preview', command)
        payload = {'kind': 'chapters', 'title': data.summary, 'command': command, 'preview': preview}
        self.chapter_edits += 1
        result = await self._propose(proposal_id, payload)
        self.invalidate_business_reads()
        return result

    async def recycle_teaching_activity(self, data, name):
        catalog = self.activity_catalog
        if not catalog or not any(a['id'] == str(data.activity_id) and a['kind'] == data.kind for a in catalog['activities']):
            raise HTTPException(409, '请先读取课程活动列表并使用其中的标识')
        if self.recycle_count >= 2:
            raise HTTPException(422, '本轮最多移入两项作业或练习')
        proposal_id = getattr(self,'operation_id',None) or str(uuid.uuid4())
        command = {'id': proposal_id, 'expected_version': catalog['course_version'],
                   'kind': data.kind, 'action': 'archive', 'target_ids': [str(data.activity_id)]}
        preview = await self._chapter_call('trash-preview', command)
        target=next(a for a in catalog['activities'] if a['id']==str(data.activity_id))
        payload = {'kind': 'recycle', 'title': '移入回收站', 'command': command, 'preview': preview,'memory_chapter_id':target.get('chapter_id')}
        self.recycle_count += 1
        result = await self._propose(proposal_id, payload)
        self.invalidate_business_reads()
        return result

    async def delegate_assistant(self, data, name):
        if self.scope.role != 'teacher' or not self.scope.allow_delegate or self._delegate is None:
            raise HTTPException(403, '当前执行角色不能委派助教')
        s = self.scope
        # Do not update self.context/have_read: delegation is not the teacher's
        # explicit read-before-write and must not silently upgrade its version.
        snapshot = await teaching.call(s.cookie, s.user.id, s.course_id, s.origin)
        return await self._delegate(data,snapshot,operation_id=self.operation_id) if getattr(self,'operation_id',None) else await self._delegate(data,snapshot)


    async def list_course_extensions(self, data, name):
        from . import extensions
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return [{'id':e['id'],'name':e['name'],'kind':e['kind'],'revision':e['revision'],'description':e['data'].get('description',''),'file_count':len(e['data'].get('files',[]))} for e in extensions.enabled(s.user,s.course_id)]

    async def load_course_skill(self, data, name):
        from . import extensions
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        result=extensions.skill_file(s.user,s.course_id,str(data.extension_id))
        entry=extensions.enabled_one(s.user,s.course_id,str(data.extension_id))
        result['files']=[f['path'] for f in entry['data'].get('files',[])]
        self.loaded_skills.add('user:'+str(data.extension_id)+':'+str(result['revision']))
        return result

    async def read_skill_file(self, data, name):
        from . import extensions
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        if 'user:'+str(data.extension_id)+':'+str(data.revision) not in self.loaded_skills:
            raise HTTPException(409,'请先加载此技能的当前版本')
        return extensions.skill_file(s.user,s.course_id,str(data.extension_id),data.path,data.offset,data.revision)

    async def list_mcp_tools(self, data, name):
        from .mcp_calls import tools_for
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return tools_for(s.user,s.course_id,s.role)

    async def call_mcp_read_tool(self, data, name):
        from .mcp_calls import request
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return await request(s,data,'read',getattr(self,'operation_id',None))

    async def call_mcp_write_tool(self, data, name):
        from .mcp_calls import request
        s=self.scope
        await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return await request(s,data,'write',getattr(self,'operation_id',None))

    async def run_sandbox(self,data,name):
        from . import sandbox,recovery
        if data.skill_id and 'user:'+str(data.skill_id)+':'+str(data.skill_revision) not in self.loaded_skills:
            raise HTTPException(409,'请先加载当前版本Skill再执行脚本')
        try:return await sandbox.request(self.scope,data,getattr(self,'operation_id',None))
        except HTTPException as exc:
            if exc.status_code==503 and recovery.CURRENT.get():raise recovery.RetryableStep() from None
            raise

    async def list_generated_artifacts(self,data,name):
        from . import sandbox
        s=self.scope;await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return [{'id':r['id'],'title':r['title'],'role':r['role'],'status':r['status'],'files':r['result'].get('files',[]),'error':r['error']} for r in sandbox.listing(s.user,s.course_id)]

    async def read_generated_artifact(self,data,name):
        from . import sandbox
        s=self.scope;await teaching.call(s.cookie,s.user.id,s.course_id,s.origin)
        return sandbox.read_artifact(s.user,s.course_id,str(data.id),data.offset)

