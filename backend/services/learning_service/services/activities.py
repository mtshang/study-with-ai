from .changes import record_change
from ..repositories import activities as repository
import uuid, hashlib, json, logging
from datetime import timezone
from common.errors import BusinessError as HTTPException
from ..models import ActivityRecord, SubmissionRecord, MaterialRecord
logger = logging.getLogger(__name__)
MAX_FILE_BYTES = 10 * 1024 * 1024
from .courses import owned

def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def question_public(q):
    return {'id': q['id'], 'prompt': q['prompt'], 'explanation': '', **({'python':q['python']} if q.get('python') else {}), **({'options': q['options']} if q.get('options') else {})}

def activity_public(activity):
    data = {'id': activity.id, 'title': activity.title, 'description': activity.description, 'source': activity.source, 'questions': [question_public(q) for q in activity.questions]}
    if activity.chapter_id:
        data['chapterId'] = activity.chapter_id
    return data

def submission_public(record, activity, db=None):
    attachments=[]
    for item in record.snapshot.get('attachments',[]):
        material=db.get(MaterialRecord,item['id']) if db is not None else None
        attachments.append({**item,**({'deleted':True} if db is not None and (not material or material.kind=='deleted') else {})})
    return {'id': record.id, 'targetId': activity.id, 'kind': activity.kind, 'targetTitle':record.snapshot.get('title',activity.title), 'targetDeleted':activity.trash_state=='deleted', 'targetTrashed':activity.trash_state=='trash', 'answers': record.answers, 'createdAt': record.created_at.replace(tzinfo=timezone.utc).isoformat(), 'questions': record.snapshot['questions'], 'attachments': attachments, **record.result}

def course_activities(db, course_id):
    activities = list(repository.list_activities(db, course_id))
    exercises = []
    assignments = []
    events = []
    by_id = {a.id: a for a in activities}
    for activity in activities:
        if activity.trash_state!='active': continue
        item = activity_public(activity)
        if activity.kind == 'exercise':
            exercises.append({**item['questions'][0], 'source': activity.source, **({'chapterId': activity.chapter_id} if activity.chapter_id else {})})
        else:
            assignments.append(item)
        events.append({'id': activity.id, 'time': activity.created_at.replace(tzinfo=timezone.utc).isoformat(), 'category': '练习' if activity.kind == 'exercise' else '作业', 'text': f'发布：{activity.title}'})
    records = list(repository.list_course_submissions(db, course_id))
    submissions = [submission_public(s, by_id[s.activity_id], db) for s in records]
    for submission in submissions:
        events.append({'id': submission['id'], 'time': submission['createdAt'], 'category': '提交', 'text': '提交作答（AI 已批改）' if submission['verdict']=='reviewed' else '提交作答（待批改）' if submission['verdict'] == 'pending' else '提交作答（客观题已核对）'})
    return (exercises, assignments, submissions, events)

def get_activity(db, course_id, activity_id, lock=False):
    result = repository.find_activity(db, course_id, activity_id, lock)
    if result is None:
        raise HTTPException(404, '练习或作业不存在或无权访问')
    return result

def course_response(db, course):
    from .courses import public
    return public(db, course)

def publish(course_id, data, db, user):
    course = owned(db, course_id, user.id, lock=True)
    signature_data = data.model_dump(mode='json', exclude={'source','expected_version'})
    for question in signature_data['questions']:
        if question.get('python') is None:question.pop('python',None)
    if data.source != 'user' or data.expected_version is not None:
        signature_data.update(source=data.source,expected_version=data.expected_version)
    signature = fingerprint(signature_data)
    existing = repository.find_publication_request(db, data)
    if existing:
        if existing.course_id != course.id or existing.request_hash != signature:
            raise HTTPException(409, '发布标识已使用，请核对已有内容后重新创建')
        db.commit()
        return course_response(db, course)
    if data.expected_version is not None and course.version != data.expected_version:
        raise HTTPException(409, '课程已经更新，请基于最新内容重新生成练习或作业')
    if data.chapter_id:
        chapter = repository.find_chapter(db, course, data)
        if chapter is None or chapter.archived:
            raise HTTPException(422, '只能关联本课程内未移出的章节')
    questions = []
    for q in data.questions:
        questions.append({**q.model_dump(), 'id': str(data.id) if data.kind == 'exercise' else str(uuid.uuid4())})
    repository.add(db, ActivityRecord(id=str(data.id), course_id=course.id, chapter_id=str(data.chapter_id) if data.chapter_id else None, kind=data.kind, title=data.title, description=data.description, source=data.source, questions=questions, request_hash=signature))
    record_change(db, course, 'activity.published', data.id, '发布练习或作业')
    db.commit()
    return course_response(db, course)

def grade(questions, answers):
    results = []
    notes = []
    correct_count = 0
    objective_count = 0
    for q in questions:
        if q.get('options'):
            objective_count += 1
            correct = answers[q['id']] == q['correct']
            correct_count += int(correct)
            verdict = 'correct' if correct else 'incorrect'
            notes.append(f"{('回答正确' if correct else '回答错误')}：{q['prompt']}\n参考答案：{q['correct']}\n{q['explanation']}")
            results.append({'questionId': q['id'], 'verdict': verdict, 'correct': q['correct'], 'explanation': q['explanation'], 'gradingMethod': 'exact_choice'})
        else:
            results.append({'questionId': q['id'], 'verdict': 'pending', 'gradingMethod': 'ungraded'})
    pending = len(questions) - objective_count
    verdict = 'pending' if pending else 'correct' if correct_count == objective_count else 'incorrect'
    summary = f'客观题已核对：{correct_count} / {objective_count} 题正确。' if objective_count else '作答已保存。'
    if pending:
        summary += f' {pending} 道主观题待批改；本次内容暂未启用自动批改，不判断其正确性。'
    return {'verdict': verdict, 'feedback': summary + ('\n\n' + '\n\n'.join(notes) if notes else ''), 'results': results, 'correctCount': correct_count, 'objectiveCount': objective_count, 'pendingCount': pending}

def submit(course_id, activity_id, data, db, user):
    course = owned(db, course_id, user.id, lock=True)
    activity = get_activity(db, course.id, activity_id, lock=True)
    attachment_ids = sorted((str(id) for id in data.attachments))
    signature = fingerprint({'answers': data.answers, 'attachments': attachment_ids}) if attachment_ids else fingerprint(data.answers)
    existing = repository.find_submission_request(db, activity, data)
    if existing:
        if existing.request_hash != signature:
            raise HTTPException(409, '本次提交标识对应另一份答案或附件，请重新发起作答')
        db.commit()
        return {'course': course_response(db, course), 'submission': submission_public(existing, activity, db)}
    if activity.trash_state!='active': raise HTTPException(409,'该作业或练习已移入回收站或删除，不能继续提交')
    if any(q.get('python') for q in activity.questions):raise HTTPException(422,'代码题请使用提交并运行入口')
    question_ids = {q['id'] for q in activity.questions}
    if set(data.answers) != question_ids:
        raise HTTPException(422, '请完整回答本练习或作业的题目，不能包含其他题目或附件字段')
    for q in activity.questions:
        if q.get('options') and data.answers[q['id']] not in q['options']:
            raise HTTPException(422, '请选择题目提供的选项')
    attachments = []
    if attachment_ids:
        if activity.kind != 'assignment':
            raise HTTPException(422, '只有作业可以附带文件')
        from .materials import file_location
        records = list(repository.list_attachment_records(db, attachment_ids, course))
        if len(records) != len(attachment_ids):
            raise HTTPException(422, '请选择本课程中已上传的文件')
        by_id = {record.id: record for record in records}
        for id in attachment_ids:
            material = by_id[id]
            if not file_location(user, course.id, id).is_file():
                raise HTTPException(422, '附件原文件不可用，请重新上传后选择')
            attachments.append({'id': id, 'filename': material.filename, 'size': material.size})
    result = grade(activity.questions, data.answers)
    if attachments:
        result.update(verdict='pending', pendingAttachmentCount=len(attachments))
        result['feedback'] += f'\n\n{len(attachments)} 份附件已保存，待评阅；尚未读取或批改附件内容。'
    record = SubmissionRecord(id=str(uuid.uuid4()), activity_id=activity.id, request_id=str(data.request_id), request_hash=signature, answers=data.answers, snapshot={**activity_public(activity), 'attachments': attachments}, result=result)
    repository.add(db, record)
    db.flush()
    from .grading import create as create_grade
    create_grade(db,record,activity)
    record_change(db, course, 'submission.created', record.id, '提交作答')
    db.commit()
    return {'course': course_response(db, course), 'submission': submission_public(record, activity, db)}

def history(course_id, activity_id, db, user):
    course = owned(db, course_id, user.id)
    activity = get_activity(db, course.id, activity_id)
    records = repository.list_activity_submissions(db, activity)
    return [submission_public(record, activity, db) for record in records]
