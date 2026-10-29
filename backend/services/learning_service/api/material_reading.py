from uuid import UUID
from fastapi import APIRouter,Depends,Query
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import material_reading
router=APIRouter(prefix='/api/courses')
@router.get('/{course_id}/reading-materials')
def listing(course_id:UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return material_reading.listing(db,user,course_id)
@router.get('/{course_id}/materials/{material_id}/text')
def read(course_id:UUID,material_id:UUID,offset:int=Query(0,ge=0,le=200000),limit:int=Query(6000,ge=1,le=6000),source_sha256:str|None=Query(None,pattern='^[0-9a-f]{64}$'),db=Depends(get_db),user=Depends(workspace_user)):
    return material_reading.read(db,user,course_id,material_id,offset,limit,source_sha256)
