from sqlalchemy import select
from ..models import User,LoginSession,utcnow

def add(db,record): db.add(record)
def add_all(db,records): db.add_all(records)

def lock_user(db, user):
    return db.scalar(select(User).where(User.id == user.id).with_for_update())
