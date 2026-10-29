import uuid
import httpx
from fastapi import HTTPException
from common import config

def read_current_course(cookie, user_id, course_id):
    """Read-only teaching tool transport. Identity is supplied by verified runtime context."""
    course_id=str(uuid.UUID(str(course_id)))
    try:
        with httpx.Client(timeout=10,trust_env=False) as client:
            response=client.get(config.LEARNING_URL+f"/api/courses/{course_id}/context",
                headers={"cookie":cookie,"x-workspace-user":user_id})
        if response.status_code in (401,403,404,409):
            raise HTTPException(response.status_code,"无法读取课程，请检查身份和课程归属")
        if response.status_code!=200: raise HTTPException(503,"教学业务服务暂不可用")
        return response.json()
    except (httpx.HTTPError,ValueError):
        raise HTTPException(503,"教学业务服务暂不可用") from None
