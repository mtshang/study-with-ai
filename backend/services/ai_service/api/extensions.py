import io
import uuid
import zipfile
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from .chat import user_context
from ..schemas.extensions import ConnectorSave, Revision, ToolPolicy, BindingSave, OutcomeReview
from ..services import extensions, skill_packages, mcp_calls
from ..clients import teaching

router=APIRouter(prefix='/api/ai')

@router.get('/extensions')
def library(user=Depends(user_context)):
    return extensions.catalog(user)

@router.post('/extensions/skills')
async def import_skill(id:uuid.UUID=Form(),name:str=Form(),files:list[UploadFile]=File(),user=Depends(user_context)):
    if len(files)>skill_packages.MAX_ENTRIES:raise HTTPException(422,'技能文件数量超过限制')
    contents=[];total=0
    for f in files:
        raw=await f.read(skill_packages.MAX_UPLOAD+1);total+=len(raw)
        if total>skill_packages.MAX_UPLOAD:raise HTTPException(422,'上传总量最多10MB')
        contents.append((f.filename or '',raw))
    if len(contents)==1 and '/' not in contents[0][0]:
        filename,raw=contents[0]
    else:
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
            for filename,raw in contents:archive.writestr(skill_packages.safe_name(filename),raw)
        filename,raw='folder.zip',output.getvalue()
    return extensions.import_skill(user,str(id),name,raw,filename)

@router.put('/extensions/mcp')
def save_connector(data:ConnectorSave,user=Depends(user_context)):
    return extensions.save_connector(user,data)

@router.post('/extensions/{eid}/discover')
async def discover(eid:uuid.UUID,data:Revision,user=Depends(user_context)):
    return await extensions.discover_connector(user,str(eid),data.revision)

@router.put('/extensions/{eid}/tools')
def policies(eid:uuid.UUID,data:ToolPolicy,user=Depends(user_context)):
    return extensions.policies(user,str(eid),data)

@router.post('/extensions/{eid}/delete')
def remove(eid:uuid.UUID,data:Revision,user=Depends(user_context)):
    return extensions.remove(user,str(eid),data.revision)

async def check(user,cid,request):
    return await teaching.call(request.headers.get('cookie',''),user.id,str(cid),request.headers.get('origin',''))

@router.get('/courses/{cid}/extensions')
async def bindings(cid:uuid.UUID,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    return extensions.bindings(user,str(cid))

@router.put('/courses/{cid}/extensions')
async def save_bindings(cid:uuid.UUID,data:BindingSave,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    return extensions.bindings(user,str(cid),data)

@router.get('/courses/{cid}/mcp-calls')
async def calls(cid:uuid.UUID,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    return mcp_calls.history(user,str(cid))

@router.post('/courses/{cid}/mcp-calls/{iid}/review')
async def review(cid:uuid.UUID,iid:uuid.UUID,data:OutcomeReview,request:Request,user=Depends(user_context)):
    await check(user,cid,request)
    return mcp_calls.review_outcome(user,str(cid),str(iid),data.note)
