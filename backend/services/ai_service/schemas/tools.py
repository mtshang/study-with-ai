from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

from common.python_exercise import PythonExercise

class CodeResultArgs(BaseModel):
    model_config=ConfigDict(extra="forbid")
    submission_id:UUID

class PythonExerciseArgs(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title:str=Field(min_length=1,max_length=200)
    prompt:str=Field(min_length=1,max_length=3000)
    chapter_id:UUID|None=None
    python:PythonExercise

class ExerciseArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=200)
    prompt:str=Field(min_length=1,max_length=3000)
    options:list[str]|None=Field(default=None,min_length=2,max_length=10)
    correct:str|None=None
    explanation:str=Field(default='',max_length=3000)
    chapter_id:UUID|None=None
    @model_validator(mode='after')
    def valid(self):
        if not self.title.strip() or not self.prompt.strip(): raise ValueError('empty')
        if self.options is not None:
            if any(not o.strip() or len(o)>200 for o in self.options) or len(set(self.options))!=len(self.options) or self.correct not in self.options: raise ValueError('invalid options')
        elif self.correct is not None: raise ValueError('open question cannot be exactly graded')
        return self

class AssignmentQuestion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    prompt:str=Field(min_length=1,max_length=3000)
    options:list[str]|None=Field(default=None,min_length=2,max_length=10)
    correct:str|None=None
    explanation:str=Field(default='',max_length=3000)
    @model_validator(mode='after')
    def valid(self):
        ExerciseArgs(title='question',**self.model_dump())
        return self

class AssignmentArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=200)
    description:str=Field(default='',max_length=2000)
    chapter_id:UUID|None=None
    questions:list[AssignmentQuestion]=Field(min_length=2,max_length=10)
    @model_validator(mode='after')
    def valid(self):
        if not self.title.strip(): raise ValueError('empty title')
        return self

class SkillArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    skill_id:Literal['read-pdf','read-docx','read-pptx']

class MaterialArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    material_id:UUID
    offset:int=Field(default=0,ge=0,le=200000)
    source_sha256:str|None=Field(default=None,pattern='^[0-9a-f]{64}$')

class DelegateArgs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    role:str=Field(min_length=1,max_length=100)
    task:str=Field(min_length=1,max_length=6000)
    @model_validator(mode='after')
    def not_blank(self):
        if not self.role.strip() or not self.task.strip(): raise ValueError('empty task')
        return self

TOOLS=[{'type':'function','function':{'name':'get_current_course','description':'读取本课程当前章节、路线与已有练习、作业。发布前必须读取。','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
       {'type':'function','function':{'name':'publish_exercise','description':'根据已读取的课程发布一道练习，或生成待用户批准的草稿。只能操作当前课程。correct 必须是完整选项文本；开放题不提供 options 和 correct。','parameters':ExerciseArgs.model_json_schema()}},
       {'type':'function','function':{'name':'publish_assignment','description':'发布一份2至10题作业或保存待批准草稿，可关联已读取的本课程章节。题目可混合客观题与开放题。correct为完整选项文本。当前只自动批改文字答案，附件不自动批改。','parameters':AssignmentArgs.model_json_schema()}},
       {'type':'function','function':{'name':'delegate_assistant','description':'异步委派一个只返回总结的助教。role 和 task 由教师编写，需包含任务目标、必要背景和期望输出。助教可调用当前课程已授权的读取工具，也可按沙箱批准规则执行 Python 或已启用 Skill 脚本并生成辅助文件；不能发布或修改正式教学内容、写入课程记忆或再委派。教师可立即继续工作，结果稍后送达。','parameters':DelegateArgs.model_json_schema()}}]

TOOLS.extend([
 {'type':'function','function':{'name':'list_course_materials','description':'列出当前课程资料及可用读取Skill。仅限本课程，不抓取网址。','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
 {'type':'function','function':{'name':'load_reading_skill','description':'按需加载内置PDF、Word或课件读取技能，随后用受控工具读取资料。','parameters':SkillArgs.model_json_schema()}},
 {'type':'function','function':{'name':'read_course_material','description':'读取已列出资料的文字片段。Office/PDF先加载对应Skill；TXT/Markdown和笔记可直接读。按next_offset续读并传source_sha256；引用返回的来源，不编造页码。','parameters':MaterialArgs.model_json_schema()}}
])

from common.chapter_contract import ChapterPlan,ChapterRead
TOOLS.extend([
 {'type':'function','function':{'name':'get_course_outline','description':'读取当前课程完整章节目录、顺序、完成及移出状态和版本。改章节前必须调用，不可依赖截断的课程概览。','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
 {'type':'function','function':{'name':'read_chapter','description':'按本课程真实章节ID读取完整正文和当前版本。修改正文前必须调用。','parameters':ChapterRead.model_json_schema()}},
 {'type':'function','function':{'name':'edit_course_chapters','description':'基于刚读取的完整目录，提交最多10项章节操作。add新增由系统分配ID；update仅改指定字段且须先read_chapter；move的after_id为null表示移到开头；add未指定after_id则追加。archive移出未完成章节但保留历史，restore恢复未完成章节。不得操作已完成章节或变更阅读状态；每次修改后须重新读目录再修改。完全手动需批准，部分批准/完全访问直接执行。','parameters':ChapterPlan.model_json_schema()}}
])

from common.recycle_contract import RecycleActivityArgs
TOOLS.extend([
 {'type':'function','function':{'name':'list_teaching_activities','description':'读取本课程仍在使用的作业和练习标识、标题及版本，移入回收站前必须调用。','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
 {'type':'function','function':{'name':'recycle_teaching_activity','description':'将本课程一项作业或练习移入回收站，保留已有提交。不支持永久删除、清空或操作资料/Skill/MCP。完全手动需批准，部分批准/完全访问可直接执行。','parameters':RecycleActivityArgs.model_json_schema()}}
])

TOOLS.append({'type':'function','function':{'name':'publish_python_exercise','description':'发布一道Python标准输入输出练习，1至3个公开测试用例，标准库、禁网。只能创建题目，不能运行代码。学生明确提交后才运行；预期输出应核对无误。','parameters':PythonExerciseArgs.model_json_schema()}})

TOOLS.append({'type':'function','function':{'name':'read_code_submission','description':'读取本课程已提交Python代码的完整代码、题目快照及受长度限制的实际运行结果。只读，不能执行或重跑代码；输入近期学习记录中的提交ID。','parameters':CodeResultArgs.model_json_schema()}})

from .memory import MemoryCommand
TOOLS.extend([
 {'type':'function','function':{'name':'read_course_memory','description':'读取本课程内部教学记忆及待确认事项，不向用户展示列表。记忆是参考，不覆盖教学服务业务事实。','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
 {'type':'function','function':{'name':'manage_course_memory','description':'教师记录或停用本课程长期教学记忆。稳定key、expected_version来自读取；新条目为0。student_statement必须引用本轮学生原话；ai_judgment可引用本轮原话或真实工具结果并提供evidence_call_id。冲突必设conflict=true并列affected操作类型。局部冲突填写affected_chapters真实章节ID，整条路线冲突才留空；用question自然语言二次确认，确认前不执行依赖操作。相同key的内容变更也强制确认。manual模式普通记录也需批准。助教只能建议，不能调用。','parameters':MemoryCommand.model_json_schema()}}
])
