import uuid
from fastapi import APIRouter,Depends,Request
from fastapi.responses import FileResponse
from .chat import user_context
from ..schemas.chat import ProposalDecision
from ..services import sandbox
from ..clients import teaching
router=APIRouter(prefix='/api/ai/courses/{cid}')
async def check(user,cid,request):await teaching.call(request.headers.get('cookie',''),user.id,str(cid),request.headers.get('origin',''))
@router.get('/sandbox-runs')
async def listing(cid:uuid.UUID,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    for row in sandbox.listing(user,str(cid))[:5]:
        if row['status'] in ('running','interrupted') and row['id'] not in sandbox.active:
            try:sandbox.persist(user,str(cid),row['id'],await sandbox.runner.request(row['id']))
            except Exception:pass # A read only reconciles available receipts; never starts code.
    return sandbox.listing(user,str(cid))
@router.post('/sandbox-runs/{iid}/decision')
async def decide(cid:uuid.UUID,iid:uuid.UUID,data:ProposalDecision,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    return await sandbox.decide(user,str(cid),str(iid),data.approve,request.headers.get('cookie',''),request.headers.get('origin',''))
@router.post('/sandbox-runs/{iid}/continue')
async def resume(cid:uuid.UUID,iid:uuid.UUID,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    return await sandbox.enqueue(user,str(cid),str(iid),request.headers.get('cookie',''),request.headers.get('origin',''))
@router.get('/artifacts/{aid}/download')
async def download(cid:uuid.UUID,aid:uuid.UUID,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    path,item=sandbox.artifact(user,str(cid),str(aid))
    return FileResponse(path,filename=item['name'].split('/')[-1],media_type='application/octet-stream',content_disposition_type='attachment',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'"})
