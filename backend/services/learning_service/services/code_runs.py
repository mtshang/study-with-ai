"""Student-triggered code attempts; persisted before dispatch, never replayed implicitly."""
import uuid
from sqlalchemy import select
from common.errors import BusinessError
from ..models import ActivityRecord,SubmissionRecord,CourseRecord
from ..infrastructure.database import SessionLocal
from ..clients import execution
from .activities import fingerprint,activity_public,submission_public,get_activity
from .courses import owned
from .changes import record_change

def normalize(value):return value.replace('\r\n','\n').rstrip('\n')

def start(db,user,cid,aid,data):
    course=owned(db,cid,user.id,lock=True);activity=get_activity(db,course.id,aid,lock=True)
    signature=fingerprint({'code':data.code,'mode':'python-io-v1'})
    existing=db.scalar(select(SubmissionRecord).where(SubmissionRecord.activity_id==activity.id,SubmissionRecord.request_id==str(data.id)))
    if existing:
        if existing.request_hash!=signature:raise BusinessError(409,'该运行标识已用于其他代码')
        db.commit();return submission_public(existing,activity),False
    if course.archived or activity.trash_state!='active':raise BusinessError(409,'课程或练习已移出，不能开始新运行')
    if activity.kind!='exercise' or len(activity.questions)!=1 or not activity.questions[0].get('python'):raise BusinessError(422,'不是Python练习')
    if db.scalar(select(SubmissionRecord.id).join(ActivityRecord).where(ActivityRecord.course_id==course.id,SubmissionRecord.result['codeRun']['status'].as_string()=='running').limit(1)):
        raise BusinessError(409,'本课程已有代码运行，请等待完成')
    q=activity.questions[0]
    state={'status':'running','cases':[],'total':len(q['python']['cases']),'passed':0,'comparison':'normalize_crlf_ignore_final_newlines','error':''}
    row=SubmissionRecord(id=str(uuid.uuid4()),activity_id=activity.id,request_id=str(data.id),request_hash=signature,
        answers={q['id']:data.code},snapshot={**activity_public(activity),'attachments':[]},
        result={'verdict':'pending','feedback':'代码已保存，正在运行公开测试用例。','codeRun':state,'results':[],'pendingCount':1})
    db.add(row);db.flush();record_change(db,course,'code.started',row.id,'提交Python代码并运行');db.commit()
    return submission_public(row,activity),True

def history(db,user,cid,aid):
    course=owned(db,cid,user.id);activity=get_activity(db,course.id,aid)
    rows=db.scalars(select(SubmissionRecord).where(SubmissionRecord.activity_id==activity.id).order_by(SubmissionRecord.created_at.desc()).limit(30))
    return [submission_public(row,activity) for row in rows if row.result.get('codeRun')]

def save(sid,case=None,finish=False,error=''):
    with SessionLocal() as db:
        row=db.get(SubmissionRecord,sid)
        if not row:return
        activity=db.get(ActivityRecord,row.activity_id)
        course=owned(db,activity.course_id,db.get(CourseRecord,activity.course_id).owner_id,lock=True)
        db.refresh(row)
        state=dict(row.result['codeRun'])
        if state['status']!='running':return
        state['cases']=[*state['cases'],*([case] if case else [])]
        state['passed']=sum(c['passed'] for c in state['cases'])
        result=dict(row.result)
        if finish:
            state.update(status='unavailable' if error else 'completed',error=error)
            result.update(verdict='pending' if error else 'correct' if state['passed']==state['total'] else 'incorrect',
                pendingCount=1 if error else 0,
                feedback=error or f"Python公开用例通过 {state['passed']} / {state['total']}。通过这些用例不等于程序对所有输入都正确。")
            record_change(db,course,'code.finished',sid,'保存Python运行结果')
        result['codeRun']=state;row.result=result;db.commit()

def run(sid):
    try:
        with SessionLocal() as db:
            row=db.get(SubmissionRecord,sid)
            if not row or row.result['codeRun']['status']!='running':return
            question=row.snapshot['questions'][0];code=row.answers[question['id']];cases=question['python']['cases']
        for number,case in enumerate(cases,1):
            result=execution.execute(code,case['stdin'],str(uuid.uuid4()))
            passed=result['status']=='completed' and result['exit_code']==0 and normalize(result['stdout'])==normalize(case['expected_stdout'])
            save(sid,{'number':number,**case,**result,'passed':passed})
            if result['status']=='unavailable':
                save(sid,finish=True,error='执行环境不可用，未完成用例不判为答案错误；请稍后重新提交。');return
        save(sid,finish=True)
    except Exception:
        # Transport and validation failures may follow actual execution. Never auto-replay.
        save(sid,finish=True,error='运行未完成或结果未确认，已保存代码和已有结果；请稍后重新提交。')

def recover():
    with SessionLocal() as db:
        rows=db.scalars(select(SubmissionRecord).where(SubmissionRecord.result['codeRun']['status'].as_string()=='running'))
        for row in rows:
            result=dict(row.result);state=dict(result['codeRun']);state.update(status='interrupted',error='教学服务重启，本次运行已中断，请重新提交。')
            result.update(codeRun=state,feedback=state['error'],verdict='pending');row.result=result
        db.commit()


def evidence(db,user,cid,sid):
    course=owned(db,cid,user.id)
    row=db.scalar(select(SubmissionRecord).join(ActivityRecord).where(ActivityRecord.course_id==course.id,SubmissionRecord.id==str(sid)))
    if not row or not row.result.get('codeRun'):raise BusinessError(404,'代码提交不存在或无权访问')
    activity=db.get(ActivityRecord,row.activity_id);question=row.snapshot['questions'][0]
    data=submission_public(row,activity);state=data['codeRun']
    data['codeRun']={**state,'cases':[{**c,'stdout':c['stdout'][:4000],'stderr':c['stderr'][:2000],
        'evidence_truncated':len(c['stdout'])>4000 or len(c['stderr'])>2000} for c in state['cases']]}
    data['course_version']=course.version;return data
