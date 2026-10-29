from common.database import connect
from .config import settings
engine,SessionLocal=connect(settings)
def get_db():
    with SessionLocal() as db:
        yield db
