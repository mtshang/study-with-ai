from common.task_auth import headers as task_headers
import httpx
from fastapi import HTTPException
from common.config import LEARNING_URL,SERVICE_KEY

async def call(user,course_id,submission_id,cookie,origin,payload=None,question_id=None):
    path=f'/api/courses/{course_id}/submissions/{submission_id}/grading'+('/input' if payload is None else '')
    if question_id is not None: path+='/items/'+str(question_id)
    try:
        async with httpx.AsyncClient(timeout=15,trust_env=False) as client:
            response=await client.request('GET' if payload is None else 'PUT',LEARNING_URL+path,json=payload,
                headers={**task_headers(cookie,user.id,origin),'x-service-key':SERVICE_KEY})
        if response.status_code!=200:
            detail={401:'登录已失效，批改保留，请重新登录后继续',403:'无权处理批改',404:'提交不存在或无权访问',409:'该提交的批改版本发生冲突',422:'该提交不支持批改或结果未通过校验'}.get(response.status_code,'批改记录服务暂不可用')
            raise HTTPException(response.status_code if response.status_code in (401,403,404,409,422) else 503,detail)
        return response.json()
    except (httpx.HTTPError,ValueError): raise HTTPException(503,'批改结果保存状态待核对，请重试；不会重新生成已保存的模型结果') from None
