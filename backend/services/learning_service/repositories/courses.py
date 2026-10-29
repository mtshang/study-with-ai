from sqlalchemy import select
from ..models import CourseRecord,ChapterRecord,CourseRevision,ActivityRecord,SubmissionRecord,MaterialRecord,utcnow

def add(db,record): db.add(record)
def add_all(db,records): db.add_all(records)

def find_owned(db, course_id, user_id, lock):
    query = select(CourseRecord).where(CourseRecord.id == str(course_id), CourseRecord.owner_id == user_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)

def list_chapters(db, record, lock):
    query = select(ChapterRecord).where(ChapterRecord.course_id == record.id, ChapterRecord.deleted == False).order_by(ChapterRecord.position)
    if lock:
        query = query.with_for_update()
    return db.scalars(query)

def recent_revisions(db, record):
    return db.scalars(select(CourseRevision).where(CourseRevision.course_id == record.id).order_by(CourseRevision.version.desc()).limit(100))

def list_owned(db, user):
    return db.scalars(select(CourseRecord).where(CourseRecord.owner_id == user.id).order_by(CourseRecord.created_at.desc()))

def get_by_id(db, course_id):
    return db.get(CourseRecord, course_id)

def find_existing_chapter_id(db, new_ids):
    return db.scalar(select(ChapterRecord.id).where(ChapterRecord.id.in_(new_ids)).limit(1))

def find_revision(db, record, version):
    return db.scalar(select(CourseRevision).where(CourseRevision.course_id == record.id, CourseRevision.version == version))
