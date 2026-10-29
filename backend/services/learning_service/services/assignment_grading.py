"""Per-question progress in one locked submission grade; objective outcomes are preserved."""
import copy,uuid
from common.errors import BusinessError
from ..models import GradeRecord,utcnow
from .changes import record_change

def create(db,record,activity):
    questions=[{'question_id':q['id'],'question':q['prompt'],'answer':record.answers[q['id']],
        'reference':q.get('explanation',''),'number':i+1} for i,q in enumerate(activity.questions) if not q.get('options')]
    if not questions: return
    from .activities import fingerprint
    snapshot={'kind':'assignment','submission_id':record.id,'activity_id':activity.id,'title':activity.title,
        'questions':questions,'rubric_version':'concept-v1','pending_attachment_count':len(record.snapshot.get('attachments',[])),
        'objective_results':[{**r,'number':i+1,'question':q['prompt'],'answer':record.answers[q['id']]} for i,q in enumerate(activity.questions) for r in record.result['results'] if r['questionId']==q['id'] and r['gradingMethod']=='exact_choice']}
    row=GradeRecord(id=str(uuid.uuid4()),submission_id=record.id,input=snapshot,input_hash=fingerprint(snapshot),
        result={'items':{q['question_id']:{'status':'waiting','result':None,'error':'','model':''} for q in questions}})
    db.add(row);db.flush();project(record,row)

def public_items(row):
    return [{'question_id':q['question_id'],'number':q['number'],'question':q['question'],**row.result['items'][q['question_id']]} for q in row.input['questions']]

def project(record,row):
    from .grading import public
    items=row.result['items'];done=sum(i['status']=='completed' for i in items.values())
    pending=len(items)-done;attachments=row.input.get('pending_attachment_count',0)
    outcomes=[]
    for item in record.result['results']:
        q=items.get(item['questionId'])
        if q:
            item={'questionId':item['questionId'],'verdict':'reviewed' if q['status']=='completed' else 'pending',
                'gradingMethod':'ai_concept',**({'mastery':q['result']['mastery']} if q['result'] else {})}
        outcomes.append(item)
    objectives=record.result['objectiveCount'];correct=record.result['correctCount']
    feedback=f'客观题已核对：{correct} / {objectives} 题正确。' if objectives else ''
    feedback+=f' 开放题已批改：{done} / {len(items)} 题。'
    if pending: feedback+=f' {pending} 道题待批改。'
    if attachments: feedback+=f' {attachments} 份附件仍待评阅，本次未读取附件。'
    record.result={**record.result,'verdict':'pending' if pending or attachments else 'reviewed','pendingCount':pending,
        'feedback':feedback.strip(),'results':outcomes,'aiGrade':public(row)}

def save_item(db,user,course_id,submission_id,question_id,data):
    from .grading import owned_grade,public
    course,record,row=owned_grade(db,user,course_id,submission_id,lock=True)
    if row.input.get('kind')!='assignment': raise BusinessError(422,'该提交不是逐题批改作业')
    if row.input_hash!=data.input_hash: raise BusinessError(409,'批改输入版本不匹配')
    question_id=str(question_id)
    question=next((q for q in row.input['questions'] if q['question_id']==question_id),None)
    if not question: raise BusinessError(404,'该题不属于本次作业的开放题')
    items=copy.deepcopy(row.result['items']);item=items[question_id]
    result=data.result.model_dump() if data.result else None
    if item['status']=='completed':
        if data.status=='completed' and (item['result']!=result or item['model']!=data.model): raise BusinessError(409,'该题已有评价，不能覆盖')
        db.commit();return public(row)
    if result and any(q not in question['answer'] for q in result['evidence']): raise BusinessError(422,'批改依据没有对应本题答案原文')
    item.update(status=data.status,result=result,error='' if result else data.error,model=data.model)
    row.result={'items':items};row.updated_at=utcnow()
    statuses=[i['status'] for i in items.values()]
    row.status='completed' if all(s=='completed' for s in statuses) else 'running' if 'running' in statuses else 'waiting' if 'waiting' in statuses else 'failed'
    failed=sum(s=='failed' for s in statuses)
    row.error=f'{failed} 道题尚未批改完成，可重试未完成题；已完成结果保留。' if failed else ''
    if row.status=='completed': record_change(db,course,'submission.graded',record.id,'保存整份作业的文字答案批改结果')
    project(record,row);db.commit();return public(row)
