from alembic import op
from services.identity_service.migrations.schema_v1 import Base
revision="0001_identity"
down_revision=None
branch_labels=None
depends_on=None
def upgrade(): Base.metadata.create_all(op.get_bind())
def downgrade(): raise RuntimeError("Destructive baseline downgrade is not supported; restore a verified backup")
