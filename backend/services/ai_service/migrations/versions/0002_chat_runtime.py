from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0002_ai_chat'
down_revision='0001_ai'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('ai_profiles', sa.Column('owner_id',sa.String(36),primary_key=True),sa.Column('permission',sa.String(16),nullable=False))
    op.create_table('chat_runs',
        sa.Column('id',sa.String(36),primary_key=True),sa.Column('owner_id',sa.String(36),nullable=False),
        sa.Column('course_id',sa.String(36),nullable=False),sa.Column('active_key',sa.String(80),unique=True),
        sa.Column('prompt',sa.Text,nullable=False),sa.Column('answer',sa.Text,nullable=False),
        sa.Column('status',sa.String(24),nullable=False),sa.Column('progress',sa.String(200),nullable=False),
        sa.Column('error',sa.String(300),nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False),
        sa.Column('updated_at',DATETIME(fsp=6),nullable=False))
    op.create_index('ix_chat_runs_owner_id','chat_runs',['owner_id'])
    op.create_index('ix_chat_runs_course_id','chat_runs',['course_id'])
    op.create_table('tool_proposals',sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('run_id',sa.String(36),sa.ForeignKey('chat_runs.id',ondelete='CASCADE'),nullable=False),
        sa.Column('payload',sa.JSON,nullable=False),sa.Column('status',sa.String(24),nullable=False),sa.Column('error',sa.String(300),nullable=False))
    op.create_index('ix_tool_proposals_run_id','tool_proposals',['run_id'])

def downgrade():
    raise RuntimeError('Chat history must be backed up before destructive downgrade')
