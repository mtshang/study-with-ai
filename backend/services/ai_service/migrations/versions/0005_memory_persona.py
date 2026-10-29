from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision='0005_ai_memory'
down_revision='0004_ai_grading'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('persona_defaults',sa.Column('owner_id',sa.String(36),primary_key=True),sa.Column('revision',sa.Integer,primary_key=True),sa.Column('prompt',sa.Text,nullable=False),sa.Column('created_at',DATETIME(fsp=6),nullable=False))
    op.create_table('course_personas',sa.Column('owner_id',sa.String(36),primary_key=True),sa.Column('course_id',sa.String(36),primary_key=True),sa.Column('prompt',sa.Text,nullable=False),sa.Column('version',sa.Integer,nullable=False),sa.Column('source_revision',sa.Integer,nullable=False))
    op.create_table('course_memories',sa.Column('owner_id',sa.String(36),primary_key=True),sa.Column('course_id',sa.String(36),primary_key=True),sa.Column('key',sa.String(80),primary_key=True),sa.Column('category',sa.String(24),nullable=False),sa.Column('content',sa.Text,nullable=False),sa.Column('evidence',sa.JSON,nullable=False),sa.Column('version',sa.Integer,nullable=False),sa.Column('active',sa.Boolean,nullable=False),sa.Column('updated_at',DATETIME(fsp=6),nullable=False))

def downgrade():
    raise RuntimeError('Back up course memory and persona history before destructive changes')
