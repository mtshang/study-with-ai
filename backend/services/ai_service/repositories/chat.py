from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert
from ..models import AgentJob, AIProfile, ChatRun, ToolProposal, utcnow, AssistantTask, CourseAgentState

def profile(db,owner_id,lock=False):
    db.execute(insert(AIProfile).values(owner_id=owner_id,permission='manual').on_duplicate_key_update(owner_id=owner_id))
    return db.scalar(select(AIProfile).where(AIProfile.owner_id==owner_id).with_for_update())

def runs(db,owner_id,course_id,limit=100):
    rows=list(db.scalars(select(ChatRun).where(ChatRun.owner_id==owner_id,ChatRun.course_id==course_id).order_by(ChatRun.created_at.desc(),ChatRun.id.desc()).limit(limit)))
    return list(reversed(rows))

def owned_run(db,owner_id,run_id):
    return db.scalar(select(ChatRun).where(ChatRun.id==run_id,ChatRun.owner_id==owner_id))

def proposals(db,run_id):
    return list(db.scalars(select(ToolProposal).where(ToolProposal.run_id==run_id).order_by(ToolProposal.id)))

def recover_interrupted(db):
    db.execute(update(AssistantTask).where(AssistantTask.status.in_(['queued','running']),~AssistantTask.id.in_(select(AgentJob.id))).values(status='interrupted',error='AI 服务重启，助教中断，需重新委派',finished_at=utcnow()))
    db.execute(update(CourseAgentState).where(~CourseAgentState.key.in_(select(AgentJob.owner_id+':'+AgentJob.course_id))).values(paused=True))
    # Durable tasks retain the user's explicit pause state.
    # Single AI process deployment. Do not replay uncertain model/tool side effects.
    db.execute(update(ChatRun).where(ChatRun.status=='running',~ChatRun.id.in_(select(AgentJob.id))).values(status='interrupted',active_key=None,error='AI 服务重启，本轮已中断；已保存的内容保留。',updated_at=utcnow()))
    db.execute(update(ToolProposal).where(ToolProposal.status=='executing',~ToolProposal.run_id.in_(select(AgentJob.id))).values(status='uncertain',error='服务中断，请重试核对同一发布标识，不会重复创建。'))
