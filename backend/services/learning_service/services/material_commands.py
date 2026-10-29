"""User material editing/removal; operation receipts make uncertain responses retryable."""
from sqlalchemy import select
from common.errors import BusinessError
from ..models import CourseRevision,utcnow
from ..repositories import materials as repository
from .courses import owned,snapshot,chapters_for
from .activities import fingerprint
from .changes import record_change
from .materials import course_response,file_location

def cleanup(user,cid,mid):
    path=file_location(user,cid,mid)
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in (path,*path.parents)):
        raise BusinessError(503,'资料已移除，但文件路径异常，请联系维护者清理')
    try:path.unlink(missing_ok=True)
    except OSError:raise BusinessError(503,'资料已移除，但原文件清理失败，请重试本次删除') from None

def apply(db,user,cid,mid,data,action):
    course=owned(db,cid,user.id,lock=True)
    signature=fingerprint({'action':action,'material_id':str(mid),**data.model_dump(mode='json')})
    receipt=db.get(CourseRevision,str(data.id))
    if receipt:
        if receipt.course_id!=course.id or receipt.snapshot.get('operation',{}).get('hash')!=signature:
            raise BusinessError(409,'操作标识已用于其他内容')
        db.commit()
        if action=='delete':cleanup(user,course.id,mid)
        return course_response(db,course)
    if course.version!=data.expected_version:raise BusinessError(409,'课程已变化，请重新载入后核对资料，本次未覆盖已有内容')
    row=repository.find_course_material(db,course,mid)
    if not row:raise BusinessError(404,'资料不存在或已删除')
    if action=='edit':
        if row.kind=='文件' and data.url:raise BusinessError(422,'文件资料不能改为链接')
        row.title=data.title;row.description=data.description
        if row.kind!='文件':
            row.url=str(data.url) if data.url else None
            row.kind='链接' if row.url else '笔记';row.source='web' if row.url else 'user'
        summary='修改课程资料'
    else:
        # Keep only identity/request receipt so a delayed upload cannot resurrect a deleted file.
        row.kind='deleted';row.title='已删除资料';row.description='';row.url=None;row.filename=None;row.size=None
        summary='删除课程资料（历史仅保留附件名称）'
    course.version+=1;course.updated_at=utcnow();db.flush()
    saved=snapshot(course,chapters_for(db,course))
    saved['operation']={'hash':signature,'kind':'material','action':action,'target':str(mid)}
    db.add(CourseRevision(id=str(data.id),course_id=course.id,version=course.version,summary=summary,snapshot=saved))
    record_change(db,course,'material.'+action,mid,summary);db.commit()
    # Metadata is inaccessible before unlink; failed cleanup is explicit and same-ID retry finishes it.
    if action=='delete':cleanup(user,course.id,mid)
    return course_response(db,course)
