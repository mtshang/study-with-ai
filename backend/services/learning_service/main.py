from common.web import create_app
from .infrastructure.config import settings
from .infrastructure.database import engine
from .api import router
app=create_app("Study with AI — learning",settings,engine)
app.include_router(router)

from contextlib import asynccontextmanager
base_lifespan=app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
    from .services.code_runs import recover
    recover()
    async with base_lifespan(application):yield
app.router.lifespan_context=lifespan
