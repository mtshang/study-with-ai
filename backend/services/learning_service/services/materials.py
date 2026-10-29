from .changes import record_change
from ..infrastructure.material_files import file_location, display_filename
from ..repositories import materials as repository
import hashlib, logging
from datetime import timezone
from common.errors import BusinessError as HTTPException
from ..models import MaterialRecord
logger = logging.getLogger(__name__)
MAX_FILE_BYTES = 10 * 1024 * 1024
from .courses import owned
from .activities import fingerprint

def public_material(record):
    result = {'id': record.id, 'title': record.title, 'kind': record.kind, 'source': record.source, 'description': record.description, 'createdAt': record.created_at.replace(tzinfo=timezone.utc).isoformat()}
    if record.url:
        result['url'] = record.url
    if record.filename:
        result.update(filename=record.filename, size=record.size, downloadable=True)
    return result

def course_materials(db, course_id):
    records = repository.list_materials(db, course_id)
    items = [public_material(r) for r in records]
    events = [{'id': m['id'], 'time': m['createdAt'], 'category': '资料', 'text': f"添加资料「{m['title']}」"} for m in items]
    return (items, events)

def course_response(db, course):
    from .courses import public
    return public(db, course)

def replay(db, course, material_id, signature):
    record = repository.find_material_request(db, material_id)
    if record and record.kind=='deleted':raise HTTPException(409, '该资料已删除，请使用新的标识重新添加')
    if record and (record.course_id != course.id or record.request_hash != signature):
        raise HTTPException(409, '资料标识已用于其他内容，请重新添加')
    return record

def create_material(course_id, data, db, user):
    course = owned(db, course_id, user.id, lock=True)
    signature = fingerprint(data.model_dump(mode='json'))
    if not replay(db, course, data.id, signature):
        repository.add(db, MaterialRecord(id=str(data.id), course_id=course.id, title=data.title, description=data.description, kind='链接' if data.url else '笔记', source='web' if data.url else 'user', url=str(data.url) if data.url else None, request_hash=signature))
        record_change(db, course, 'material.created', data.id, '添加课程资料')
    db.commit()
    return course_response(db, course)

def upload_material(course_id, material_id, body, filename, db, user):
    course = owned(db, course_id, user.id, lock=True)
    if len(body) > MAX_FILE_BYTES:
        raise HTTPException(413, '每份文件最多 10 MiB')
    name = display_filename(filename)
    signature = fingerprint({'filename': name, 'sha256': hashlib.sha256(body).hexdigest(), 'size': len(body)})
    if replay(db, course, material_id, signature):
        db.commit()
        return course_response(db, course)
    path = file_location(user, course.id, material_id)
    created = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            created = True
            stream.write(body)
        repository.add(db, MaterialRecord(id=str(material_id), course_id=course.id, title=name, kind='文件', source='user', description=f'文件大小 {len(body) / 1024:.1f} KB。原文件已保存，可下载；尚未解析内容。', filename=name, size=len(body), request_hash=signature))
        record_change(db, course, 'material.uploaded', material_id, '上传课程文件')
        db.commit()
    except Exception as exc:
        db.rollback()
        if created:
            try:
                if repository.get_material(db, material_id) is None:
                    path.unlink(missing_ok=True)
            except Exception:
                logger.error('Material reconciliation needed for %s', material_id)
        if isinstance(exc, OSError):
            raise HTTPException(503, '文件保存失败，请检查存储空间后重试') from None
        raise
    return course_response(db, course)

def download_material(course_id, material_id, db, user):
    course = owned(db, course_id, user.id)
    record = repository.find_course_material(db, course, material_id)
    if record is None or record.kind != '文件':
        raise HTTPException(404, '文件不存在或无权访问')
    path = file_location(user, course.id, record.id)
    if not path.is_file():
        raise HTTPException(404, '文件内容缺失，请检查备份或重新上传')
    return (path, record.filename)
