from sqlalchemy import select
from ..models import CourseRecord,ChapterRecord,CourseRevision,ActivityRecord,SubmissionRecord,MaterialRecord,utcnow

def add(db,record): db.add(record)
def add_all(db,records): db.add_all(records)

def list_materials(db, course_id):
    return db.scalars(select(MaterialRecord).where(MaterialRecord.course_id == course_id, MaterialRecord.kind != "deleted").order_by(MaterialRecord.created_at.desc(), MaterialRecord.id))

def find_material_request(db, material_id):
    return db.scalar(select(MaterialRecord).where(MaterialRecord.id == str(material_id)).with_for_update())

def get_material(db, material_id):
    return db.get(MaterialRecord, str(material_id))

def find_course_material(db, course, material_id):
    return db.scalar(select(MaterialRecord).where(MaterialRecord.id == str(material_id), MaterialRecord.course_id == course.id, MaterialRecord.kind != "deleted"))
