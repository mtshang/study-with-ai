from sqlalchemy import select
from ..models import CourseChange
def add(db,record): db.add(record)
def page(db,course_id,after,through,limit):
    return list(db.scalars(select(CourseChange).where(CourseChange.course_id==course_id,
        CourseChange.sequence>after,CourseChange.sequence<=through).order_by(CourseChange.sequence).limit(limit)))
