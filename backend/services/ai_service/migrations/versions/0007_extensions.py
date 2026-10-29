from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0007_ai_extensions'
down_revision='0006_ai_recovery'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('extensions',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),nullable=False,index=True),sa.Column('kind',sa.String(8),nullable=False),sa.Column('name',sa.String(100),nullable=False),sa.Column('revision',sa.Integer,nullable=False),sa.Column('data',sa.JSON,nullable=False),sa.Column('deleted',sa.Boolean,nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False))
    op.create_table('course_extensions',sa.Column('owner_id',sa.String(36),primary_key=True),sa.Column('course_id',sa.String(36),primary_key=True),sa.Column('revision',sa.Integer,nullable=False),sa.Column('enabled',sa.JSON,nullable=False))
    op.create_table('mcp_invocations',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),nullable=False,index=True),sa.Column('course_id',sa.String(36),nullable=False,index=True),sa.Column('job_id',sa.String(36),nullable=True),sa.Column('extension_id',sa.String(36),nullable=False,index=True),sa.Column('extension_revision',sa.Integer,nullable=False),sa.Column('tool',sa.String(128),nullable=False),sa.Column('effect',sa.String(12),nullable=False),sa.Column('arguments',sa.JSON,nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.Column('result',sa.JSON,nullable=True),sa.Column('error',sa.Text,nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False))
def downgrade():
    raise RuntimeError('Back up extension data before destructive rollback')
