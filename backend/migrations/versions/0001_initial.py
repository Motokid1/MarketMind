"""DATA-001 initial relational schema, FR-001/014/015/016."""
from alembic import op
import sqlalchemy as sa
revision='0001'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('users',sa.Column('id',sa.String(),primary_key=True),sa.Column('email',sa.String(),nullable=False,unique=True),sa.Column('password_hash',sa.Text(),nullable=False),sa.Column('role',sa.String(),nullable=False),sa.Column('active',sa.Boolean()),sa.Column('created_at',sa.DateTime(timezone=True)))
    op.create_table('research_runs',sa.Column('id',sa.String(),primary_key=True),sa.Column('owner_id',sa.String(),sa.ForeignKey('users.id'),nullable=False),sa.Column('params',sa.JSON(),nullable=False),sa.Column('state',sa.String()),sa.Column('result',sa.JSON()),sa.Column('created_at',sa.DateTime(timezone=True)),sa.Column('completed_at',sa.DateTime(timezone=True)))
    op.create_table('tool_registry',sa.Column('id',sa.String(),primary_key=True),sa.Column('service',sa.String(),nullable=False),sa.Column('method',sa.String(),nullable=False),sa.Column('schema_hash',sa.String(),nullable=False),sa.Column('input_schema',sa.JSON(),nullable=False),sa.Column('capability',sa.String()),sa.Column('enabled',sa.Boolean()),sa.Column('validated_at',sa.DateTime(timezone=True)))
    op.create_table('tool_invocations',sa.Column('id',sa.String(),primary_key=True),sa.Column('run_id',sa.String()),sa.Column('service',sa.String()),sa.Column('method',sa.String()),sa.Column('schema_hash',sa.String()),sa.Column('duration_ms',sa.Integer()),sa.Column('status',sa.String()),sa.Column('error_code',sa.String()),sa.Column('evidence_ref',sa.String()),sa.Column('source_as_of',sa.String()),sa.Column('timestamp',sa.DateTime(timezone=True)))
    op.create_table('market_observations',sa.Column('id',sa.String(),primary_key=True),sa.Column('run_id',sa.String(),sa.ForeignKey('research_runs.id')),sa.Column('lineage',sa.JSON()),sa.Column('source_as_of',sa.String()),sa.Column('fetched_at',sa.String()))
    op.create_table('calculated_metrics',sa.Column('id',sa.String(),primary_key=True),sa.Column('run_id',sa.String(),sa.ForeignKey('research_runs.id')),sa.Column('name',sa.String()),sa.Column('value',sa.JSON()),sa.Column('formula_version',sa.String()),sa.Column('input_ids',sa.JSON()))
    op.create_table('reports',sa.Column('id',sa.String(),primary_key=True),sa.Column('run_id',sa.String(),sa.ForeignKey('research_runs.id')),sa.Column('owner_id',sa.String(),sa.ForeignKey('users.id')),sa.Column('shared_with',sa.JSON()),sa.Column('annotations',sa.JSON()),sa.Column('generated_at',sa.DateTime(timezone=True)),sa.Column('retention_until',sa.DateTime(timezone=True)))
    op.create_table('audit_events',sa.Column('id',sa.String(),primary_key=True),sa.Column('actor_id',sa.String()),sa.Column('action',sa.String()),sa.Column('entity_id',sa.String()),sa.Column('status',sa.String()),sa.Column('timestamp',sa.DateTime(timezone=True)))
def downgrade():
    for table in ('audit_events','reports','calculated_metrics','market_observations','tool_invocations','tool_registry','research_runs','users'):
        op.drop_table(table)
