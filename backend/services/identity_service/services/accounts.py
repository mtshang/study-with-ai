import logging
import secrets
import uuid
from datetime import timedelta
from common.errors import BusinessError as HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from common.config import Settings
from ..models import User, LoginSession, utcnow
from ..schemas.accounts import Credentials
from ..repositories import accounts as repositories
from common import storage
from ..infrastructure.security import password_hasher, verify_password, DUMMY_HASH, digest
logger = logging.getLogger(__name__)

def register(db: Session, credentials: Credentials, config: Settings) -> User:
    key = credentials.username.casefold()
    if repositories.find_user(db, key):
        raise HTTPException(409, '该用户名已被注册')
    user_id = str(uuid.uuid4())
    dirname = storage.storage_name(credentials.username, user_id)
    user = User(id=user_id, username=credentials.username, username_key=key, password_hash=password_hasher.hash(credentials.password.get_secret_value()), storage_dir=dirname)
    created = False
    try:
        repositories.add(db, user)
        db.flush()
        storage.provision(config.user_root, dirname, user_id)
        created = True
        db.commit()
    except Exception as exc:
        db.rollback()
        if created:
            try:
                if repositories.get_user(db, user_id) is None:
                    storage.remove_new_directory(config.user_root, dirname)
            except Exception:
                logger.error('Registration cleanup needs reconciliation for user %s', user_id)
        if isinstance(exc, IntegrityError):
            raise HTTPException(409, '该用户名已被注册') from None
        if isinstance(exc, OSError):
            raise HTTPException(503, '无法创建用户文件目录，请稍后再试') from None
        raise
    return user

def login(db: Session, credentials: Credentials, config: Settings, previous_token: str | None):
    user = repositories.find_user(db, credentials.username.casefold())
    valid = verify_password(credentials.password.get_secret_value(), user.password_hash if user else DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(401, '用户名或密码错误')
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(credentials.password.get_secret_value())
    if previous_token:
        repositories.revoke_session(db, digest(previous_token))
    repositories.prune_user_sessions(db, user.id)
    token = secrets.token_urlsafe(32)
    repositories.add(db, LoginSession(token_hash=digest(token), user_id=user.id, expires_at=utcnow() + timedelta(seconds=config.session_seconds)))
    db.commit()
    return (user, token)
