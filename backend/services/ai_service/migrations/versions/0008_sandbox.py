from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0008_ai_sandbox'
down_revision='0007_ai_extensions'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('sandbox_runs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),nullable=False,index=True),sa.Column('course_id',sa.String(36),nullable=False,index=True),sa.Column('task_id',sa.String(36),nullable=True),sa.Column('role',sa.String(16),nullable=False),sa.Column('title',sa.String(120),nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.Column('request',sa.JSON,nullable=False),sa.Column('sources',sa.JSON,nullable=False),sa.Column('result',sa.JSON,nullable=False),sa.Column('error',sa.Text,nullable=False),sa.Column('attempts',sa.Integer,nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False))
def downgrade():raise RuntimeError('Back up sandbox history before destructive rollback')
