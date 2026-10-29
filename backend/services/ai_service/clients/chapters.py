from common.task_auth import headers as task_headers
import httpx
from fastapi import HTTPException
from common.config import LEARNING_URL,SERVICE_KEY

async def call(cookie,owner,cid,origin,action,payload=None,chapter_id=None):
    suffix={'code-result':f'/code-runs/{chapter_id}','outline':'/outline','read':f'/chapters/{chapter_id}','preview':'/chapter-changes/preview','apply':'/chapter-changes','activities':'/teaching-activities','trash-preview':'/ai-trash-preview','trash':'/ai-trash-actions'}[action]
    headers=task_headers(cookie,owner,origin)
    if payload is not None: headers['x-service-key']=SERVICE_KEY
    try:
        async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
            response=await client.request('POST' if payload is not None else 'GET',LEARNING_URL+f'/api/courses/{cid}'+suffix,headers=headers,json=payload)
        if response.status_code!=200:
            status=response.status_code if response.status_code in (401,403,404,409,422) else 503
            detail=response.json().get('detail') if status in (409,422) else None
            raise HTTPException(status,detail if isinstance(detail,str) else '章节操作失败，请核对登录、课程归属及当前版本')
        return response.json()
    except (httpx.HTTPError,ValueError): raise HTTPException(503,'章节服务连接中断，请按原操作标识核对结果') from None
