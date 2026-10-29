from common.task_auth import headers as task_headers
import httpx
from fastapi import HTTPException
from common.config import LEARNING_URL
async def call(cookie,user_id,cid,mid=None,params=None):
    path=f'/api/courses/{cid}'+('/reading-materials' if mid is None else f'/materials/{mid}/text')
    try:
        async with httpx.AsyncClient(timeout=40,trust_env=False) as client:
            response=await client.get(LEARNING_URL+path,params=params,headers=task_headers(cookie,user_id))
        if response.status_code!=200:
            messages={401:'登录已失效',404:'资料不存在或不属于本课程',409:'资料版本变化，请重新读取',422:'该资料无法读取；格式、内容或读取位置不支持，扫描件需OCR',429:'解析繁忙，请稍后重试'}
            raise HTTPException(response.status_code,messages.get(response.status_code,'资料读取服务暂不可用'))
        return response.json()
    except (httpx.HTTPError,ValueError): raise HTTPException(503,'资料读取连接失败') from None

async def download(cookie,user_id,cid,mid):
    path=f'/api/courses/{cid}/materials/{mid}/download'
    try:
        async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
            async with client.stream('GET',LEARNING_URL+path,headers=task_headers(cookie,user_id)) as response:
                if response.status_code!=200:raise HTTPException(response.status_code,'输入资料不存在或无权访问')
                data=bytearray()
                async for part in response.aiter_bytes():
                    data.extend(part)
                    if len(data)>5*1024*1024:raise HTTPException(422,'沙箱输入总量最多5MB')
                return bytes(data)
    except httpx.HTTPError:raise HTTPException(503,'输入文件读取失败') from None

