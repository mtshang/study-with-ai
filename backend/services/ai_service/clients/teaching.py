from common.task_auth import headers as task_headers
import httpx
from fastapi import HTTPException
from common.config import LEARNING_URL,SERVICE_KEY

async def changes(cookie,user_id,course_id,origin,after,through):
    result=[]
    async with httpx.AsyncClient(timeout=15,trust_env=False) as client:
        while after<through:
            try:
                response=await client.get(LEARNING_URL+f'/api/courses/{course_id}/changes',params={'after':after,'limit':200},headers=task_headers(cookie,user_id,origin))
                if response.status_code!=200: raise HTTPException(503,'暂时无法读取课程变更；助教结果尚未确认')
                rows=response.json()['changes']
                selected=[r for r in rows if after<r['sequence']<=through]
                if not selected: raise HTTPException(503,'课程变更记录不完整，暂不确认助教结果')
                for row in selected:
                    if row['sequence']!=after+1: raise HTTPException(503,'课程变更顺序不连续')
                    result.append(row);after=row['sequence']
            except (httpx.HTTPError,ValueError,KeyError,TypeError): raise HTTPException(503,'课程变更读取失败') from None
    return result

async def call(cookie,user_id,course_id,origin,payload=None):
    headers=task_headers(cookie,user_id,origin)
    if payload is not None: headers['x-service-key']=SERVICE_KEY
    path=f'/api/courses/{course_id}'+('/context' if payload is None else '/activities')
    try:
        async with httpx.AsyncClient(timeout=15,trust_env=False) as client:
            response=await client.request('GET' if payload is None else 'POST',LEARNING_URL+path,headers=headers,json=payload)
        if response.status_code!=200:
            detail={401:'登录已失效',403:'无权执行操作',404:'课程不存在或无权访问',409:'课程或发布状态已变化，请重新读取后生成',422:'教学服务拒绝了练习或作业参数'}.get(response.status_code,'教学服务暂不可用')
            raise HTTPException(response.status_code if response.status_code in (401,403,404,409,422) else 503,detail)
        return response.json()
    except (httpx.HTTPError,ValueError): raise HTTPException(503,'教学服务连接中断；发布结果需按同一标识核对') from None
