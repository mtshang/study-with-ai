import httpx
from fastapi import HTTPException
from common import config
from common.identity import Principal
from common.task_auth import PREFIX,headers,decode
async def issue(user,cid,tid,cookie,origin):
    if cookie.startswith(PREFIX):
        claims=decode(cookie[len(PREFIX):])
        if claims['owner']!=user.id or claims['course']!=cid:raise HTTPException(403,'后台授权范围不匹配')
        from common.task_auth import encode
        return PREFIX+encode({**claims,'task':tid})
    try:
        async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
            r=await client.post(config.IDENTITY_URL+f'/api/internal/task-grants/{cid}/{tid}',headers={**headers(cookie,user.id,origin),'x-service-key':config.SERVICE_KEY})
        if r.status_code!=200:raise HTTPException(401 if r.status_code==401 else 503,'无法建立后台任务授权')
        return PREFIX+r.json()['grant']
    except (httpx.HTTPError,ValueError,KeyError):raise HTTPException(503,'后台任务授权服务暂不可用') from None
async def resolve(credential,owner,cid):
    try:
        async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
            r=await client.get(config.IDENTITY_URL+'/api/internal/task-principal',headers=headers(credential,owner))
        if r.status_code!=200:raise HTTPException(401 if r.status_code==401 else 503,'后台任务授权失效或暂不可用')
        data=r.json()
        if data['id']!=owner or data['course_id']!=cid:raise HTTPException(403,'后台任务授权范围不匹配')
        return Principal(data['id'],data['username'],data['storage_dir'])
    except (httpx.HTTPError,ValueError,KeyError):raise HTTPException(503,'后台任务授权服务暂不可用') from None
