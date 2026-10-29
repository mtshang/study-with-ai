from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..infrastructure import config
from ..infrastructure.database import get_db
from ..schemas.accounts import Credentials, UserPublic
from ..services import accounts as services
from ..repositories import accounts as repositories
from ..infrastructure.security import COOKIE, digest, auth_limiter

router = APIRouter(prefix="/api")

def auth_limit(request: Request):
    auth_limiter.check(request.client.host if request.client else "unknown")

def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 128:
        raise HTTPException(401, "请先登录")
    user = repositories.session_user(db, digest(token))
    if not user: raise HTTPException(401, "登录已失效，请重新登录")
    return user

@router.get("/health")
def health(): return {"status": "ok"}

@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1 FROM users LIMIT 1"))
    db.execute(text("SELECT 1 FROM login_sessions LIMIT 1"))
    return {"status":"ready","database":"mysql","service":"identity"}

@router.post("/auth/register", response_model=UserPublic, status_code=201, dependencies=[Depends(auth_limit)])
def register(credentials: Credentials, db: Session = Depends(get_db)):
    return services.register(db, credentials, config.settings)

@router.post("/auth/login", response_model=UserPublic, dependencies=[Depends(auth_limit)])
def login(credentials: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    user, token = services.login(db, credentials, config.settings, request.cookies.get(COOKIE))
    response.set_cookie(COOKIE, token, max_age=config.settings.session_seconds, httponly=True,
                        secure=config.settings.cookie_secure, samesite="strict", path="/api")
    return user

@router.get("/auth/me", response_model=UserPublic)
def me(user=Depends(current_user)): return user

@router.post("/auth/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        repositories.revoke_session(db, digest(token))
        db.commit()
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/api", secure=config.settings.cookie_secure, httponly=True, samesite="strict")
    return response

from common import config as internal_config
import secrets

@router.get("/internal/principal")
def principal(request: Request, user=Depends(current_user)):
    key=internal_config.SERVICE_KEY
    if not key or not secrets.compare_digest(request.headers.get("x-service-key", ""),key):
        raise HTTPException(403,"内部服务身份无效")
    return {"id":user.id,"username":user.username,"storage_dir":user.storage_dir}

def workspace_user(request: Request, user=Depends(current_user)):
    if request.headers.get("x-workspace-user")!=user.id:
        raise HTTPException(409,"登录账号已变化，请重新载入个人空间")
    return user
