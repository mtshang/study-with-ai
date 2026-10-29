import uuid
from fastapi import APIRouter, Depends, Request
from .chat import user_context
from ..schemas.memory import PersonaUpdate
from ..services import persona
from ..clients import teaching
from ..infrastructure.database import SessionLocal
router=APIRouter(prefix='/api/ai')

@router.get('/persona')
def get_default(user=Depends(user_context)):
    with SessionLocal() as db:return persona.global_view(db,user.id)

@router.put('/persona')
def put_default(data:PersonaUpdate,user=Depends(user_context)):
    return persona.save_default(user.id,data)

@router.get('/courses/{course_id}/persona')
async def get_course(course_id:uuid.UUID,request:Request,user=Depends(user_context)):
    context=await teaching.call(request.headers.get('cookie',''),user.id,str(course_id),request.headers.get('origin',''))
    return persona.course_view(user.id,str(course_id),context)

@router.put('/courses/{course_id}/persona')
async def put_course(course_id:uuid.UUID,data:PersonaUpdate,request:Request,user=Depends(user_context)):
    context=await teaching.call(request.headers.get('cookie',''),user.id,str(course_id),request.headers.get('origin',''))
    return persona.course_view(user.id,str(course_id),context,data)

@router.get('/courses/{course_id}/confirmations')
async def confirmations(course_id:uuid.UUID,request:Request,user=Depends(user_context)):
    from ..services import memory
    await teaching.call(request.headers.get('cookie',''),user.id,str(course_id),request.headers.get('origin',''))
    with SessionLocal() as db:return [memory.public_proposal(p) for p in memory.pending(db,user.id,str(course_id))]
