from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..infrastructure.database import get_db
from .accounts import workspace_user
from ..schemas.preferences import DisplayPreferences,DisplayUpdate
from ..services import preferences as service
router=APIRouter(prefix="/api/preferences",tags=["preferences"])


@router.get('/display', response_model=DisplayPreferences)
def get_display(user=Depends(workspace_user)):
    return service.get_display(user)

@router.put('/display', response_model=DisplayPreferences)
def put_display(data: DisplayUpdate, db: Session=Depends(get_db), user=Depends(workspace_user)):
    return service.put_display(data, db, user)
