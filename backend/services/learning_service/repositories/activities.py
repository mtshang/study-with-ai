from sqlalchemy import select
from ..models import CourseRecord,ChapterRecord,CourseRevision,ActivityRecord,SubmissionRecord,MaterialRecord,utcnow

def add(db,record): db.add(record)
def add_all(db,records): db.add_all(records)

def list_activities(db, course_id):
    return db.scalars(select(ActivityRecord).where(ActivityRecord.course_id == course_id).order_by(ActivityRecord.created_at))

def list_course_submissions(db, course_id):
    return db.scalars(select(SubmissionRecord).join(ActivityRecord, SubmissionRecord.activity_id == ActivityRecord.id).where(ActivityRecord.course_id == course_id).order_by(SubmissionRecord.created_at.desc(), SubmissionRecord.id))

def find_activity(db, course_id, activity_id, lock):
    query = select(ActivityRecord).where(ActivityRecord.course_id == course_id, ActivityRecord.id == str(activity_id))
    if lock:
        query = query.with_for_update()
    return db.scalar(query)

def find_publication_request(db, data):
    return db.scalar(select(ActivityRecord).where(ActivityRecord.id == str(data.id)).with_for_update())

def find_chapter(db, course, data):
    return db.scalar(select(ChapterRecord).where(ChapterRecord.id == str(data.chapter_id), ChapterRecord.course_id == course.id, ChapterRecord.deleted == False).with_for_update())

def find_submission_request(db, activity, data):
    return db.scalar(select(SubmissionRecord).where(SubmissionRecord.activity_id == activity.id, SubmissionRecord.request_id == str(data.request_id)).with_for_update())

def list_attachment_records(db, attachment_ids, course):
    return db.scalars(select(MaterialRecord).where(MaterialRecord.course_id == course.id, MaterialRecord.id.in_(attachment_ids), MaterialRecord.kind == '文件'))

def list_activity_submissions(db, activity):
    return db.scalars(select(SubmissionRecord).where(SubmissionRecord.activity_id == activity.id).order_by(SubmissionRecord.created_at.desc(), SubmissionRecord.id))
