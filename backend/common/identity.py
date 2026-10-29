from dataclasses import dataclass
import re
import httpx
from fastapi import Request,HTTPException
from common import config

@dataclass(frozen=True)
class Principal:
    id: str
    username: str
    storage_dir: str

def resolve_principal(request: Request):
    """Verify the session remotely; never accept a user ID supplied by the caller."""
    if not config.SERVICE_KEY: raise HTTPException(503,"服务间身份校验尚未配置")
    grant=request.headers.get('x-task-grant')
    if grant:
        from common.task_auth import require_service
        require_service(request)
        from common.task_auth import permit_path
        permit_path(request.method,request.url.path)
    try:
        with httpx.Client(timeout=5,trust_env=False) as client:
            response=client.get(config.IDENTITY_URL+("/api/internal/task-principal" if grant else "/api/internal/principal"),
                headers={"cookie":request.headers.get("cookie",""),"x-service-key":config.SERVICE_KEY,**({"x-task-grant":grant} if grant else {})})
        if response.status_code==401: raise HTTPException(401,"请先登录或重新登录")
        if response.status_code!=200: raise HTTPException(503,"账号服务暂不可用")
        result=response.json()
        if grant:
            if request.url.path.split('/')[3]!=result.pop('course_id'):
                raise HTTPException(403,'后台授权不能跨课程使用')
            result.pop('task_id')
        return Principal(**result)
    except (httpx.HTTPError,ValueError,TypeError):
        raise HTTPException(503,"账号服务暂不可用") from None

def require_workspace(request: Request, user):
    if request.headers.get("x-workspace-user")!=user.id:
        raise HTTPException(409,"登录账号已变化，请重新载入个人空间")
    return user
