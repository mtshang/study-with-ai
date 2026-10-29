import asyncio
from contextlib import asynccontextmanager
from common.web import create_app
from .infrastructure.config import settings
from .infrastructure.database import engine,SessionLocal
from .api import router
from .repositories.chat import recover_interrupted
from .services.runtime import tasks
from .services import assistants,recovery
from sqlalchemy import text

app=create_app('Study with AI — ai',settings,engine)
base_lifespan=app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
    async with base_lifespan(application):
        # Existing per-course in-process locks still require one AI service.
        lease_connection=engine.connect()
        lock_name='study-ai-runtime:'+settings.database
        if lease_connection.scalar(text('SELECT GET_LOCK(:name,0)'),{'name':lock_name})!=1:
            lease_connection.close();raise RuntimeError('Only one AI service process is supported')
        with SessionLocal.begin() as db: recover_interrupted(db)
        assistants.closing=False
        await recovery.startup()
        try: yield
        finally:
            assistants.closing=True
            await recovery.shutdown()
            pending=[*tasks.values(),*assistants.tasks.values()]
            for task in pending: task.cancel()
            if pending: await asyncio.gather(*pending,return_exceptions=True)
            lease_connection.execute(text('SELECT RELEASE_LOCK(:name)'),{'name':lock_name});lease_connection.close()
app.router.lifespan_context=lifespan
app.include_router(router)
