from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0006_ai_recovery'
down_revision='0005_ai_memory'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('agent_jobs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),nullable=False,index=True),sa.Column('course_id',sa.String(36),nullable=False,index=True),sa.Column('kind',sa.String(16),nullable=False),sa.Column('credential',sa.Text,nullable=False),sa.Column('origin',sa.String(200),nullable=False),sa.Column('status',sa.String(24),nullable=False,index=True),sa.Column('generation',sa.Integer,nullable=False),sa.Column('recoveries',sa.Integer,nullable=False),sa.Column('lease_owner',sa.String(36)),sa.Column('lease_until',DATETIME(fsp=6)),sa.Column('payload',sa.JSON,nullable=False),sa.Column('drafts',sa.JSON,nullable=False),sa.Column('error',sa.String(300),nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False),sa.Column('updated_at',DATETIME(fsp=6),nullable=False))
    op.create_table('agent_steps',sa.Column('job_id',sa.String(36),sa.ForeignKey('agent_jobs.id',ondelete='CASCADE'),primary_key=True),sa.Column('key',sa.String(160),primary_key=True),sa.Column('kind',sa.String(16),nullable=False),sa.Column('status',sa.String(16),nullable=False),sa.Column('request',sa.JSON,nullable=False),sa.Column('result',sa.JSON),sa.Column('tool_state',sa.JSON,nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False))
    op.create_table('agent_checkpoints',sa.Column('job_id',sa.String(36),sa.ForeignKey('agent_jobs.id',ondelete='CASCADE'),primary_key=True),sa.Column('checkpoint_id',sa.String(80),primary_key=True),sa.Column('data',sa.JSON,nullable=False))
    op.create_table('agent_checkpoint_writes',sa.Column('job_id',sa.String(36),sa.ForeignKey('agent_jobs.id',ondelete='CASCADE'),primary_key=True),sa.Column('checkpoint_id',sa.String(80),primary_key=True),sa.Column('task_id',sa.String(80),primary_key=True),sa.Column('idx',sa.Integer,primary_key=True),sa.Column('channel',sa.String(200),nullable=False),sa.Column('value',sa.JSON,nullable=False))
def downgrade():raise RuntimeError('Back up task state before destructive rollback')
