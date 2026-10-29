from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def connect(settings):
    engine=create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5,
                         hide_parameters=True, connect_args={"connect_timeout":5,"read_timeout":10,"write_timeout":10})
    return engine,sessionmaker(bind=engine,expire_on_commit=False)
