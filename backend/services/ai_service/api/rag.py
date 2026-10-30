from uuid import UUID
from fastapi import APIRouter,Depends,Request
from .chat import user_context
from ..schemas.rag import IndexRequest,SearchRequest
from ..services import rag
router=APIRouter(prefix='/api/ai/courses/{cid}/rag')
@router.get('')
async def listing(cid:UUID,request:Request,user=Depends(user_context)):
    return await rag.catalog(user,str(cid),request.headers.get('cookie',''))
@router.post('/index')
async def index(cid:UUID,data:IndexRequest,request:Request,user=Depends(user_context)):
    return await rag.enqueue(user,str(cid),data,request.headers.get('cookie',''),request.headers.get('origin',''))
@router.post('/search')
async def search(cid:UUID,data:SearchRequest,request:Request,user=Depends(user_context)):
    return await rag.search(user,str(cid),request.headers.get('cookie',''),data)
@router.post('/cleanup')
async def cleanup(cid:UUID,request:Request,user=Depends(user_context)):
    return await rag.cleanup(user,str(cid),request.headers.get('cookie',''))
