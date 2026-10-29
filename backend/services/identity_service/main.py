from common.web import create_app
from .infrastructure.config import settings
from .infrastructure.database import engine
from .api import router
app=create_app("Study with AI — identity",settings,engine)
app.include_router(router)
