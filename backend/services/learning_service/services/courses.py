from .changes import record_change
from ..repositories import courses as repository
import uuid, hashlib, json, logging
from datetime import timezone
from sqlalchemy.exc import IntegrityError
from common.errors import BusinessError as HTTPException
from ..models import CourseRecord, ChapterRecord, CourseRevision, utcnow
logger = logging.getLogger(__name__)
MAX_FILE_BYTES = 10 * 1024 * 1024

def owned(db, course_id, user_id, lock=False):
    record = repository.find_owned(db, course_id, user_id, lock)
    if record is None:
        raise HTTPException(404, '课程不存在或无权访问')
    return record

def chapters_for(db, record, lock=False):
    return list(repository.list_chapters(db, record, lock))

def snapshot(record, chapters):
    return {'id': record.id, 'title': record.title, 'goal': record.goal, 'category': record.category, 'color': record.color, 'icon': record.icon, 'source': record.source, 'template_id': record.template_id, 'archived': record.archived, 'currentChapterId': record.current_chapter_id, 'version': record.version, 'chapters': [{'id': ch.id, 'title': ch.title, 'description': ch.description, 'content': ch.content, 'read': ch.read, 'archived': ch.archived, 'source': ch.source} for ch in chapters]}

def add_revision(db, record, chapters, summary):
    record_change(db, record, 'course.updated', record.id, summary)
    repository.add(db, CourseRevision(id=str(uuid.uuid4()), course_id=record.id, version=record.version, summary=summary, snapshot=snapshot(record, chapters)))

def public(db, record):
    data = snapshot(record, chapters_for(db, record))
    history = list(repository.recent_revisions(db, record))
    data.update(exercises=[], assignments=[], submissions=[], materials=[], messages=[])
    data['revisions'] = [{'id': r.id, 'version': r.version, 'time': r.created_at.replace(tzinfo=timezone.utc).isoformat(), 'summary': r.summary, 'titles': [ch['title'] for ch in r.snapshot['chapters'] if not ch['archived']]} for r in history]
    data['events'] = [{'id': r['id'], 'time': r['time'], 'text': r['summary'], 'category': '课程'} for r in data['revisions']]
    from .activities import course_activities
    exercises, assignments, submissions, events = course_activities(db, record.id)
    data.update(exercises=exercises, assignments=assignments, submissions=submissions)
    from .materials import course_materials
    data['materials'], material_events = course_materials(db, record.id)
    data['events'] = sorted(data['events'] + events + material_events, key=lambda event: event['time'], reverse=True)[:100]
    return data

def list_courses(db, user):
    records = repository.list_owned(db, user)
    return [public(db, r) for r in records]

def get_course(course_id, db, user):
    return public(db, owned(db, course_id, user.id))

def create_course(data, db, user):
    signature = hashlib.sha256(json.dumps(data.model_dump(mode='json', exclude={'id'}), sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    course_id = str(data.id or uuid.uuid4())
    record = CourseRecord(id=course_id, owner_id=user.id, title=data.title, goal=data.goal, creation_hash=signature, archived=False, version=1, category='自主学习', color='purple', icon='book', source='user')
    repository.add(db, record)
    chapters = []
    if data.template_id is not None:
        category, color, icon = [('编程开发', 'green', 'code'), ('语言学习', 'blue', 'language'), ('设计与创意', 'orange', 'design')][data.template_id]
        record.category, record.color, record.icon = (category, color, icon)
        record.source = 'system'
        record.template_id = data.template_id
        for title, description, content in [('认识学习目标', '明确我们要解决的问题，建立第一张知识地图。', f'欢迎来到「{data.title}」。\n\n这是一份系统模板的示例章节。先思考：你希望用这门知识做什么？你已经接触过哪些内容？'), ('基础概念与第一次练习', '从一个小例子入手，边理解边尝试。', '这里将承载基础讲解与示例。你可以先在路线页面编辑章节，再安排对应练习。')]:
            chapters.append(ChapterRecord(id=str(uuid.uuid4()), course_id=record.id, title=title, description=description, content=content, position=len(chapters), read=False, archived=False, source='system'))
        record.current_chapter_id = chapters[0].id
    try:
        db.flush()
        repository.add_all(db, chapters)
        add_revision(db, record, chapters, '从系统模板创建课程' if chapters else '创建课程')
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = repository.get_by_id(db, course_id)
        if existing and existing.owner_id == user.id and (existing.creation_hash == signature):
            return public(db, existing)
        raise HTTPException(409, '创建标识已用于其他内容，请先核对课程列表；如需新建另一门课，请关闭后重新打开新建窗口') from None
    return public(db, record)

def update_course(course_id, data, db, user):
    record = owned(db, course_id, user.id, lock=True)
    if record.version != data.version:
        raise HTTPException(409, '课程已被其他页面修改，请重新载入后核对；本次修改未覆盖服务器数据')
    previous = chapters_for(db, record, lock=True)
    old = {ch.id: ch for ch in previous}
    ids = {str(ch.id) for ch in data.chapters}
    if not set(old).issubset(ids):
        raise HTTPException(422, '已有章节不能直接删除，请移出路线以保留历史')
    new_ids = ids - set(old)
    if new_ids and repository.find_existing_chapter_id(db, new_ids):
        raise HTTPException(422, '章节标识不可使用')
    for ch in data.chapters:
        previous_chapter = old.get(str(ch.id))
        if previous_chapter and previous_chapter.read and ch.archived and (not previous_chapter.archived):
            raise HTTPException(422, '已读章节不能直接移出路线，请先明确修改阅读状态')
    before = snapshot(record, previous)
    updated = []
    for index, ch in enumerate(data.chapters):
        item = old.get(str(ch.id))
        if item is None:
            item = ChapterRecord(id=str(ch.id), course_id=record.id, source='user')
            repository.add(db, item)
        item.title, item.description, item.content = (ch.title, ch.description, ch.content)
        if ch.archived and not item.archived:
            from .recycle import detach
            detach(db,record.id,item.id)
        item.read, item.archived, item.position = (ch.read, ch.archived, index)
        updated.append(item)
    record.title, record.goal, record.archived = (data.title, data.goal, data.archived)
    record.current_chapter_id = str(data.currentChapterId) if data.currentChapterId else None
    after = snapshot(record, updated)
    if before == after:
        db.commit()
        return public(db, record)
    changes = []
    if (before['title'], before['goal']) != (after['title'], after['goal']):
        changes.append('修改课程信息')
    if before['archived'] != after['archived']:
        changes.append('归档课程' if record.archived else '恢复课程')
    if before['currentChapterId'] != after['currentChapterId']:
        changes.append('切换当前章节')
    if before['chapters'] != after['chapters']:
        changes.append('更新章节内容、阅读状态或路线')
    record.version += 1
    record.updated_at = utcnow()
    add_revision(db, record, updated, '；'.join(changes))
    db.commit()
    return public(db, record)

def revision(course_id, version, db, user):
    record = owned(db, course_id, user.id)
    result = repository.find_revision(db, record, version)
    if result is None:
        raise HTTPException(404, '版本不存在')
    return result.snapshot
