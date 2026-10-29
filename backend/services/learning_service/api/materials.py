from fastapi.responses import FileResponse
import uuid
from typing import Annotated
from fastapi import APIRouter,Depends,File,Form,UploadFile
from sqlalchemy.orm import Session
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import materials as service
from ..schemas.materials import *
router=APIRouter(prefix="/api/courses",tags=["materials"])


@router.post('/{course_id}/materials')
def create_material(course_id: uuid.UUID, data: MaterialCreate, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.create_material(course_id, data, db, user)

@router.post('/{course_id}/materials/upload')
def upload_material(course_id: uuid.UUID, material_id: Annotated[uuid.UUID, Form()], file: Annotated[UploadFile, File()], db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.upload_material(course_id, material_id, file.file.read(service.MAX_FILE_BYTES+1), file.filename, db, user)

@router.get('/{course_id}/materials/{material_id}/download')
def download_material(course_id: uuid.UUID, material_id: uuid.UUID, db: Session=Depends(get_db), user=Depends(workspace_user)):
    path,filename=service.download_material(course_id, material_id, db, user)
    return FileResponse(path,filename=filename,media_type="application/octet-stream",content_disposition_type="attachment",headers={"X-Content-Type-Options":"nosniff","Cache-Control":"no-store"})

from fastapi import Request,HTTPException
from ..services import material_commands

@router.put('/{course_id}/materials/{material_id}')
def edit_material(course_id:uuid.UUID,material_id:uuid.UUID,data:MaterialEdit,request:Request,db:Session=Depends(get_db),user=Depends(workspace_user)):
    if request.headers.get('x-service-key'):raise HTTPException(403,'资料管理只能由用户操作')
    return material_commands.apply(db,user,course_id,material_id,data,'edit')

@router.post('/{course_id}/materials/{material_id}/delete')
def delete_material(course_id:uuid.UUID,material_id:uuid.UUID,data:MaterialDelete,request:Request,db:Session=Depends(get_db),user=Depends(workspace_user)):
    if request.headers.get('x-service-key'):raise HTTPException(403,'资料只能由用户删除')
    return material_commands.apply(db,user,course_id,material_id,data,'delete')
