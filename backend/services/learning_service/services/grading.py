"""Formal assessment belongs to learning; only authenticated service callbacks write it."""
import uuid
from datetime import timezone
from sqlalchemy import select
from common.errors import BusinessError
from common.grading_contract import MASTERY
from ..models import GradeRecord,SubmissionRecord,ActivityRecord,utcnow
from .courses import owned
from .changes import record_change

def public(row):
    assignment=row.input.get('kind')=='assignment'
    from .assignment_grading import public_items
    return {**({'kind':'assignment','items':public_items(row),'objective_results':row.input.get('objective_results',[]),'pending_attachment_count':row.input.get('pending_attachment_count',0)} if assignment else {}),
        'id':row.id,'submission_id':row.submission_id,'status':row.status,'result':None if assignment else row.result,
        'error':row.error,'model':row.model,'updated_at':row.updated_at.replace(tzinfo=timezone.utc).isoformat()}

def create(db,record,activity):
    if activity.kind=='assignment':
        from .assignment_grading import create as create_assignment
        return create_assignment(db,record,activity)
    if activity.questions[0].get('options'): return
    from .activities import fingerprint
    question=activity.questions[0]
    snapshot={'submission_id':record.id,'activity_id':activity.id,'question_id':question['id'],
        'question':question['prompt'],'answer':record.answers[question['id']],
        'reference':question.get('explanation',''),'rubric_version':'concept-v1'}
    row=GradeRecord(id=str(uuid.uuid4()),submission_id=record.id,input=snapshot,input_hash=fingerprint(snapshot))
    db.add(row);db.flush()
    record.result={**record.result,'feedback':'作答已保存，AI 批改待处理。','aiGrade':public(row)}

def owned_grade(db,user,course_id,submission_id,lock=False):
    course=owned(db,course_id,user.id,lock=lock)
    record=db.scalar(select(SubmissionRecord).join(ActivityRecord).where(SubmissionRecord.id==str(submission_id),ActivityRecord.course_id==course.id))
    if not record: raise BusinessError(404,'提交不存在或无权访问')
    query=select(GradeRecord).where(GradeRecord.submission_id==record.id)
    row=db.scalar(query.with_for_update() if lock else query)
    if not row: raise BusinessError(422,'该提交没有可自动批改的新开放题文字答案')
    return course,record,row

def context(db,user,course_id,submission_id):
    _,_,row=owned_grade(db,user,course_id,submission_id)
    return {**public(row),'input_hash':row.input_hash,'input':row.input}

def save(db,user,course_id,submission_id,data):
    course,record,row=owned_grade(db,user,course_id,submission_id,lock=True)
    if row.input.get('kind')=='assignment': raise BusinessError(422,'作业必须按题保存批改结果')
    if data.input_hash!=row.input_hash: raise BusinessError(409,'批改输入版本不匹配')
    result=data.result.model_dump() if data.result else None
    if row.status=='completed':
        if data.status=='completed' and (row.result!=result or row.model!=data.model): raise BusinessError(409,'该次提交已有批改结果，不能覆盖')
        db.commit();return public(row)
    row.status=data.status;row.error=data.error;row.updated_at=utcnow()
    if result:
        # Ground quoted evidence in the immutable answer, not arbitrary model claims.
        if any(quote not in row.input['answer'] for quote in result['evidence']): raise BusinessError(422,'批改依据没有对应本次答案原文')
        row.result=result;row.model=data.model;row.error=''
        record.result={**record.result,'verdict':'reviewed','pendingCount':0,
            'feedback':'AI 批改：'+MASTERY[result['mastery']]+'。'+result['reason'],
            'results':[{'questionId':row.input['question_id'],'verdict':'reviewed','gradingMethod':'ai_concept','mastery':result['mastery']}]}
        record_change(db,course,'submission.graded',record.id,'保存该次开放练习的 AI 批改结果')
    record.result={**record.result,'aiGrade':public(row)}
    db.commit();return public(row)
