import uuid,secrets
from fastapi import APIRouter,Depends,Request,HTTPException
from common.config import SERVICE_KEY
from common.grading_contract import GradeUpdate
from ..infrastructure.database import get_db
from .dependencies import workspace_user
from ..services import grading
router=APIRouter(prefix='/api/courses')

def trusted(request:Request):
    if not SERVICE_KEY or not secrets.compare_digest(request.headers.get('x-service-key',''),SERVICE_KEY):
        raise HTTPException(403,'批改结果只能由受信任的服务保存')

@router.get('/{course_id}/submissions/{submission_id}/grading')
def get_grade(course_id:uuid.UUID,submission_id:uuid.UUID,db=Depends(get_db),user=Depends(workspace_user)):
    _,_,row=grading.owned_grade(db,user,course_id,submission_id)
    return grading.public(row)

@router.get('/{course_id}/submissions/{submission_id}/grading/input',dependencies=[Depends(trusted)])
def input_grade(course_id:uuid.UUID,submission_id:uuid.UUID,db=Depends(get_db),user=Depends(workspace_user)):
    return grading.context(db,user,course_id,submission_id)

@router.put('/{course_id}/submissions/{submission_id}/grading',dependencies=[Depends(trusted)])
def put_grade(course_id:uuid.UUID,submission_id:uuid.UUID,data:GradeUpdate,db=Depends(get_db),user=Depends(workspace_user)):
    return grading.save(db,user,course_id,submission_id,data)


@router.put('/{course_id}/submissions/{submission_id}/grading/items/{question_id}',dependencies=[Depends(trusted)])
def put_item(course_id:uuid.UUID,submission_id:uuid.UUID,question_id:uuid.UUID,data:GradeUpdate,db=Depends(get_db),user=Depends(workspace_user)):
    from ..services.assignment_grading import save_item
    return save_item(db,user,course_id,submission_id,question_id,data)
