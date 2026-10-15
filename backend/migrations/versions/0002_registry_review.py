"""FR-003/018 persist reviewed mappings across restarts."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('tool_registry',sa.Column('reviewed_config',sa.JSON(),nullable=True))
def downgrade():
    op.drop_column('tool_registry','reviewed_config')
