import uuid
from datetime import timezone
from ..models import CourseChange
from ..repositories import changes as repository

def record_change(db, course, kind, target_id, summary):
    """Caller holds the course row lock (or is creating it); commit with the business write."""
    course.change_seq = (course.change_seq or 0) + 1
    repository.add(db, CourseChange(id=str(uuid.uuid4()), course_id=course.id, sequence=course.change_seq, course_version=course.version, actor_id=course.owner_id, kind=kind, target_id=str(target_id), summary=summary))

def changes_after(db, user, course_id, after, limit):
    from .courses import owned
    course = owned(db, course_id, user.id)
    through = course.change_seq
    records = repository.page(db, course.id, after, through, limit)
    items = [{'id': r.id, 'sequence': r.sequence, 'course_version': r.course_version, 'actor_id': r.actor_id, 'kind': r.kind, 'target_id': r.target_id, 'summary': r.summary, 'created_at': r.created_at.replace(tzinfo=timezone.utc).isoformat()} for r in records]
    return {'course_id': course.id, 'through_sequence': through, 'next_after': records[-1].sequence if records else after, 'has_more': bool(records and records[-1].sequence < through), 'changes': items}

def current_context(db, user, course_id):
    from .courses import owned, public
    course = owned(db, course_id, user.id)
    return {'course_id': course.id, 'course_version': course.version, 'change_sequence': course.change_seq, 'course_created_at': course.created_at.replace(tzinfo=timezone.utc).isoformat(), 'course': public(db, course)}
