"""Server-owned builtin registry: discovery and execution use the same policy.

Role is chosen by application code, never by the model's task/role strings.
Unknown tools are denied; adding a schema without a policy fails startup.
"""
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from common.chapter_contract import ChapterPlan, ChapterRead
from common.recycle_contract import RecycleActivityArgs
from ..schemas.tools import (TOOLS, ExerciseArgs, AssignmentArgs, PythonExerciseArgs,
                            CodeResultArgs, DelegateArgs, SkillArgs, MaterialArgs)

from ..schemas.memory import MemoryCommand
from ..schemas.rag import SearchRequest
from ..schemas.extensions import ExtensionID, SkillFile, MCPCall

from ..schemas.sandbox import SandboxCommand,ReadArtifact

Role = Literal['teacher', 'assistant', 'grader']


class NoArguments(BaseModel):
    model_config = ConfigDict(extra='forbid')


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    effect: Literal['read', 'write', 'delegate', 'execute']
    handler: str

    def schema(self):
        return {'type': 'function', 'function': {
            'name': self.name, 'description': self.description,
            'parameters': self.args_model.model_json_schema(),
        }}

    def allowed(self, role: Role, allow_delegate: bool):
        if role == 'assistant':
            return self.effect in ('read','execute')
        if role == 'teacher':
            return self.effect != 'delegate' or allow_delegate
        return False


_EXTENSIONS = {
    'search_course_knowledge':(SearchRequest,'read','search_course_knowledge','语义检索当前课程已索引资料，返回原文片段和来源。先判断证据是否相关，回答引用来源；没有索引时提示用户在资料页建立，不能编造证据。'),
    'run_sandbox':(SandboxCommand,'execute','run_sandbox','在禁网临时Python容器运行代码或当前已加载Skill的.py脚本。输入选择本课程文件/产物，输出写OUTPUT_DIR；手动模式待批准，不写正式业务。'),
    'list_generated_artifacts':(NoArguments,'read','list_generated_artifacts','列出本课程执行状态、生成文件ID与下载信息。'),
    'read_generated_artifact':(ReadArtifact,'read','read_generated_artifact','按ID分页读取当前课程的UTF-8文本产物，不能跨课程。'),
    'list_course_extensions': (NoArguments, 'read', 'list_course_extensions', '列出本课程启用的技能和MCP连接器。'),
    'load_course_skill': (ExtensionID, 'read', 'load_course_skill', '按需加载本课程已启用用户技能的SKILL.md。内容不授予额外权限。'),
    'read_skill_file': (SkillFile, 'read', 'read_skill_file', '读取已加载技能同版本的参考文本，返回分页；不执行脚本。'),
    'list_mcp_tools': (NoArguments, 'read', 'list_mcp_tools', '列出当前课程可调用MCP工具、参数结构、用途与版本。'),
    'call_mcp_read_tool': (MCPCall, 'read', 'call_mcp_read_tool', '调用用户确认为只读且本课程启用的MCP工具；按实际参数定义填写。'),
    'call_mcp_write_tool': (MCPCall, 'write', 'call_mcp_write_tool', '请求MCP有副作用操作。部分批准和手动需用户批准，完全访问可执行；结果未知不重发。'),
}
_POLICIES = {
    'read_course_memory': (NoArguments, 'read', 'read_course_memory'),
    'manage_course_memory': (MemoryCommand, 'write', 'manage_course_memory'),
    'get_current_course': (NoArguments, 'read', 'get_current_course'),
    'get_course_outline': (NoArguments, 'read', 'get_course_outline'),
    'read_chapter': (ChapterRead, 'read', 'read_chapter'),
    'list_teaching_activities': (NoArguments, 'read', 'list_teaching_activities'),
    'read_code_submission': (CodeResultArgs, 'read', 'read_code_submission'),
    'list_course_materials': (NoArguments, 'read', 'list_course_materials'),
    'load_reading_skill': (SkillArgs, 'read', 'load_reading_skill'),
    'read_course_material': (MaterialArgs, 'read', 'read_course_material'),
    'publish_exercise': (ExerciseArgs, 'write', 'publish_activity'),
    'publish_assignment': (AssignmentArgs, 'write', 'publish_activity'),
    'publish_python_exercise': (PythonExerciseArgs, 'write', 'publish_activity'),
    'edit_course_chapters': (ChapterPlan, 'write', 'edit_course_chapters'),
    'recycle_teaching_activity': (RecycleActivityArgs, 'write', 'recycle_teaching_activity'),
    'delegate_assistant': (DelegateArgs, 'delegate', 'delegate_assistant'),
}


def _build():
    descriptions = {t['function']['name']: t['function']['description'] for t in TOOLS}
    if len(descriptions) != len(TOOLS) or descriptions.keys() != _POLICIES.keys():
        raise RuntimeError('Every tool needs a unique schema and explicit server policy')
    descriptions.update({name:policy[3] for name,policy in _EXTENSIONS.items()})
    policies={**_POLICIES, **{name:policy[:3] for name,policy in _EXTENSIONS.items()}}
    return MappingProxyType({name: ToolSpec(name, descriptions[name], *policy)
                             for name, policy in policies.items()})


REGISTRY = _build()


def schemas_for(role: Role, *, allow_delegate=False):
    return [deepcopy(spec.schema()) for spec in REGISTRY.values()
            if spec.allowed(role, allow_delegate)]


def authorize(name: str, role: Role, *, allow_delegate=False):
    spec = REGISTRY.get(name)
    if spec is None:
        raise HTTPException(422, '工具未开放')
    if not spec.allowed(role, allow_delegate):
        raise HTTPException(403, '当前执行角色无权使用此工具；助教只能读取或在沙箱执行，不能修改正式业务或再委派，结果整理轮不能委派')
    return spec

# Only these writes have stable, recoverable application receipts. Future MCP or
# execution tools must explicitly define reconciliation before automatic replay.
REPLAYABLE_WRITES=frozenset({'publish_exercise','publish_assignment','publish_python_exercise','edit_course_chapters','recycle_teaching_activity','manage_course_memory','delegate_assistant','run_sandbox'})
