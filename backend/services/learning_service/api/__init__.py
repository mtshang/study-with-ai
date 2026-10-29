from fastapi import APIRouter,Depends
from sqlalchemy import text
from ..infrastructure.database import get_db
from .courses import router as courses
from .activities import router as activities
from .materials import router as materials
from .changes import router as changes
from .grading import router as grading
from .material_reading import router as material_reading
from .chapter_commands import router as chapter_commands
from .recycle import router as recycle
from .code_runs import router as code_runs
router=APIRouter()
for child in [courses,activities,materials,changes,grading,material_reading,chapter_commands,recycle,code_runs]: router.include_router(child)
@router.get("/api/health")
def health(): return {"status":"ok","service":"learning"}
@router.get("/api/ready")
def ready(db=Depends(get_db)):
    for name in ["courses","chapters","course_revisions","activities","submissions","materials","course_changes","submission_grades"]:
        db.execute(text(f"SELECT 1 FROM {name} LIMIT 1"))
    return {"status":"ready","database":"mysql","service":"learning"}
