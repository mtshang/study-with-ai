from alembic import context
from services.identity_service.infrastructure.database import engine
from services.identity_service.models import Base
if context.is_offline_mode(): raise RuntimeError("Online migrations required")
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
    with context.begin_transaction(): context.run_migrations()
