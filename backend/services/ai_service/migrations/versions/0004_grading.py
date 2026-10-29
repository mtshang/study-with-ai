from alembic import op
import sqlalchemy as sa
revision='0004_ai_grading'
down_revision='0003_ai_assistants'
branch_labels=None
depends_on=None
def upgrade():
    op.alter_column('assistant_tasks','run_id',existing_type=sa.String(36),nullable=True)
    op.add_column('assistant_tasks',sa.Column('purpose',sa.String(24),nullable=False,server_default='delegated'))
    op.add_column('assistant_tasks',sa.Column('submission_id',sa.String(36),nullable=True))
    op.create_unique_constraint('uq_assistant_submission','assistant_tasks',['submission_id'])
    op.add_column('assistant_tasks',sa.Column('payload',sa.JSON,nullable=True))
def downgrade(): raise RuntimeError('Back up grading tasks before destructive changes')
