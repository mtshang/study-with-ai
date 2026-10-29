from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from ..models import User, LoginSession, utcnow

def find_user(db: Session, username_key: str):
    return db.scalar(select(User).where(User.username_key == username_key))

def session_user(db: Session, token_hash: str):
    return db.scalar(select(User).join(LoginSession).where(
        LoginSession.token_hash == token_hash, LoginSession.expires_at > utcnow()))

def revoke_session(db: Session, token_hash: str):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash))

def prune_user_sessions(db: Session, user_id: str):
    db.execute(delete(LoginSession).where(LoginSession.user_id == user_id, LoginSession.expires_at <= utcnow()))

def add(db, record): db.add(record)
def get_user(db, user_id): return db.get(User,user_id)
