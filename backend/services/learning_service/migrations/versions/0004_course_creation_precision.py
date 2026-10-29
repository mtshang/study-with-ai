from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0004_learning_time'
down_revision='0003_learning_recycle'
branch_labels=None
depends_on=None

def upgrade():
    op.alter_column('courses','created_at',existing_type=sa.DateTime(),type_=DATETIME(fsp=6),existing_nullable=False)

def downgrade():
    raise RuntimeError('Downgrade would discard course creation timestamp precision')
