from alembic import op
import sqlalchemy as sa
revision='0003_learning_recycle'
down_revision='0002_learning_grading'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('chapters',sa.Column('deleted',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column('activities',sa.Column('trash_state',sa.String(16),nullable=False,server_default='active'))
def downgrade(): raise RuntimeError('Back up recycle and learning history before changing schema')
