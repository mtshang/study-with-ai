from fastapi import APIRouter
from .accounts import router as accounts
from .preferences import router as preferences
router=APIRouter()
router.include_router(accounts)
router.include_router(preferences)

from .task_auth import router as task_auth
router.include_router(task_auth)
