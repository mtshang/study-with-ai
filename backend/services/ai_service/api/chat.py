import asyncio,json,uuid
from typing import Literal
from fastapi import APIRouter,Depends,Request,HTTPException
from fastapi.responses import StreamingResponse
from common.identity import resolve_principal,require_workspace
from ..infrastructure.database import SessionLocal,get_db
from ..schemas.chat import ConfigUpdate,RunInput,ProposalDecision
from ..services import configuration,runtime,assistants,grading
from ..clients import teaching,model
from ..repositories import chat as repository

router=APIRouter(prefix='/api/ai')

def user_context(request:Request,user=Depends(resolve_principal)):
    return require_workspace(request,user)

@router.get('/config')
def get_config(user=Depends(user_context),db=Depends(get_db)):
    return configuration.view(user,db)

@router.put('/config')
def put_config(data:ConfigUpdate,user=Depends(user_context),db=Depends(get_db)):
    return configuration.save(user,data,db)

@router.post('/config/{channel}/test')
async def test_config(channel:Literal['chat','vision','embedding'],user=Depends(user_context)):
    if channel=='embedding':
        from ..clients.embeddings import embed
        vectors=await embed(configuration.model_config(user,channel),['连接测试'])
        return {'ok':True,'message':f'向量化连接成功，维度：{len(vectors[0])}'}
    return await model.test_connection(configuration.model_config(user,channel),channel)

@router.post('/courses/{course_id}/submissions/{submission_id}/grade')
async def grade_submission(course_id:uuid.UUID,submission_id:uuid.UUID,request:Request,user=Depends(user_context)):
    return await grading.start(user,course_id,submission_id,request.headers.get('cookie',''),request.headers.get('origin',''))

@router.get('/courses/{course_id}/agents')
async def agent_state(course_id:uuid.UUID,request:Request,user=Depends(user_context)):
    await teaching.call(request.headers.get('cookie',''),user.id,str(course_id),request.headers.get('origin',''))
    with SessionLocal() as db: return assistants.snapshot(db,user,str(course_id))

@router.post('/courses/{course_id}/pause')
async def pause_course(course_id:uuid.UUID,request:Request,user=Depends(user_context)):
    await teaching.call(request.headers.get('cookie',''),user.id,str(course_id),request.headers.get('origin',''))
    return await assistants.pause(user,str(course_id))

@router.get('/courses/{course_id}/runs')
async def list_runs(course_id:uuid.UUID,request:Request,user=Depends(user_context)):
    await teaching.call(request.headers.get('cookie',''),user.id,str(course_id),request.headers.get('origin',''))
    with SessionLocal() as db:
        return [runtime.public(db,r) for r in repository.runs(db,user.id,str(course_id))]

@router.post('/courses/{course_id}/runs')
async def start_run(course_id:uuid.UUID,data:RunInput,request:Request,user=Depends(user_context)):
    return await runtime.start(user,course_id,data,request.headers.get('cookie',''),request.headers.get('origin',''))

@router.get('/runs/{run_id}')
def get_run(run_id:uuid.UUID,user=Depends(user_context),db=Depends(get_db)):
    return runtime.public(db,runtime.get_owned(db,user,str(run_id)))

@router.post('/runs/{run_id}/stop')
async def stop_run(run_id:uuid.UUID,user=Depends(user_context)):
    return await runtime.stop(user,run_id)

@router.post('/proposals/{proposal_id}/decision')
async def decide(proposal_id:uuid.UUID,data:ProposalDecision,request:Request,user=Depends(user_context)):
    return await runtime.decide(user,proposal_id,data.approve,request.headers.get('cookie',''),request.headers.get('origin',''))

@router.get('/runs/{run_id}/events')
async def events(run_id:uuid.UUID,request:Request,user=Depends(user_context)):
    with SessionLocal() as db: runtime.get_owned(db,user,str(run_id))
    async def snapshots():
        last='';ticks=0
        while not await request.is_disconnected():
            if ticks%20==0:
                try: await asyncio.to_thread(resolve_principal,request)
                except HTTPException:
                    yield 'event: auth_error\ndata: {}\n\n';return
            with SessionLocal() as db:
                run=runtime.get_owned(db,user,str(run_id));data=runtime.public(db,run)
            payload=json.dumps(data,ensure_ascii=False)
            if payload!=last:
                yield 'data: '+payload+'\n\n';last=payload
            else: yield ': keepalive\n\n'
            if data['status']!='running': return
            ticks+=1
            await asyncio.sleep(.5)
    return StreamingResponse(snapshots(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})


@router.get('/reading-skills')
def reading_skills():
    from ..services.reading_skills import catalog
    return catalog()


@router.post('/jobs/{job_id}/resume')
async def resume_job(job_id:uuid.UUID,request:Request,user=Depends(user_context)):
    from ..services import recovery
    return await recovery.resume(user,str(job_id),request.headers.get('cookie',''),request.headers.get('origin',''))
