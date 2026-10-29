from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0002_learning_grading'
down_revision='0001_learning'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('submission_grades',sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('submission_id',sa.String(36),sa.ForeignKey('submissions.id',ondelete='CASCADE'),unique=True,nullable=False),
        sa.Column('input_hash',sa.String(64),nullable=False),sa.Column('input',sa.JSON,nullable=False),
        sa.Column('status',sa.String(24),nullable=False),sa.Column('result',sa.JSON,nullable=True),
        sa.Column('model',sa.String(120),nullable=False),sa.Column('error',sa.String(300),nullable=False),
        sa.Column('created_at',DATETIME(fsp=6),nullable=False),sa.Column('updated_at',DATETIME(fsp=6),nullable=False))
def downgrade(): raise RuntimeError('Back up grading history before destructive changes')
