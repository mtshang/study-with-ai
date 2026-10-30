"""Qdrant REST adapter. Its address is operator-owned, never supplied by a model."""
import os
import httpx
from fastapi import HTTPException

async def request(method,path,body=None,allow_missing=False):
    base=os.getenv('QDRANT_URL','http://127.0.0.1:6333').rstrip('/')
    headers={'api-key':os.environ['QDRANT_API_KEY']} if os.getenv('QDRANT_API_KEY') else {}
    try:
        async with httpx.AsyncClient(timeout=30,trust_env=False,follow_redirects=False) as client:
            response=await client.request(method,base+path,json=body,headers=headers)
        if allow_missing and response.status_code==404:return None
        if response.status_code not in (200,201):raise HTTPException(503,'向量库请求失败，请检查 Qdrant 状态')
        return response.json()['result']
    except (httpx.HTTPError,ValueError,KeyError):raise HTTPException(503,'无法连接向量库，请先启动 Qdrant') from None

async def ensure(collection,size):
    path='/collections/'+collection
    if await request('GET',path,allow_missing=True) is None:
        try:await request('PUT',path,{'vectors':{'size':size,'distance':'Cosine'}})
        except HTTPException:
            if await request('GET',path,allow_missing=True) is None:raise
    info=await request('GET',path)
    if info['config']['params']['vectors']['size']!=size:raise HTTPException(409,'向量维度与索引不匹配，请重建索引')

def filters(owner,cid,job_ids=None):
    must=[{'key':'owner_id','match':{'value':owner}},{'key':'course_id','match':{'value':cid}}]
    if job_ids is not None:must.append({'key':'job_id','match':{'any':job_ids}})
    return {'must':must}

async def upsert(collection,points):return await request('PUT',f'/collections/{collection}/points?wait=true',{'points':points})
async def query(collection,vector,owner,cid,job_ids,limit):
    if not job_ids:return []
    result=await request('POST',f'/collections/{collection}/points/query',{'query':vector,'filter':filters(owner,cid,job_ids),'limit':limit,'with_payload':True})
    return result['points']
async def remove(collection,owner,cid,job_ids):
    if job_ids:await request('POST',f'/collections/{collection}/points/delete?wait=true',{'filter':filters(owner,cid,job_ids)})
