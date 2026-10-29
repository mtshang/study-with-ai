from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0003_ai_assistants'
down_revision='0002_ai_chat'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('chat_runs',sa.Column('trigger',sa.String(16),nullable=False,server_default='user'))
    op.create_table('course_agent_states',sa.Column('key',sa.String(80),primary_key=True),
        sa.Column('owner_id',sa.String(36),nullable=False),sa.Column('course_id',sa.String(36),nullable=False),
        sa.Column('paused',sa.Boolean,nullable=False),sa.Column('change_sequence',sa.Integer,nullable=False))
    op.create_index('ix_course_agent_states_owner_id','course_agent_states',['owner_id'])
    op.create_table('assistant_tasks',sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('run_id',sa.String(36),sa.ForeignKey('chat_runs.id',ondelete='CASCADE'),nullable=False),
        sa.Column('owner_id',sa.String(36),nullable=False),sa.Column('course_id',sa.String(36),nullable=False),
        sa.Column('role',sa.String(100),nullable=False),sa.Column('prompt',sa.Text,nullable=False),
        sa.Column('status',sa.String(24),nullable=False),sa.Column('result',sa.Text,nullable=False),sa.Column('error',sa.String(300),nullable=False),
        sa.Column('consumed_by',sa.String(36),sa.ForeignKey('chat_runs.id',ondelete='SET NULL')),
        sa.Column('created_at',DATETIME(fsp=6),nullable=False),sa.Column('finished_at',DATETIME(fsp=6)))
    for field in ['run_id','owner_id','course_id']: op.create_index('ix_assistant_tasks_'+field,'assistant_tasks',[field])
    op.create_table('run_contexts',sa.Column('run_id',sa.String(36),sa.ForeignKey('chat_runs.id',ondelete='CASCADE'),primary_key=True),sa.Column('batches',sa.JSON,nullable=False))

def downgrade():
    raise RuntimeError('Back up assistant results and contexts before a destructive downgrade')
