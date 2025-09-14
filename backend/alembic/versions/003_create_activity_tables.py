"""Create activity tracking tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create activities table
    op.create_table('activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('duration_seconds', sa.String(length=20), nullable=True),
        sa.Column('related_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_deployment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['related_deployment_id'], ['deployments.id'], ),
        sa.ForeignKeyConstraint(['related_file_id'], ['project_files.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_id'), 'activities', ['id'], unique=False)
    op.create_index(op.f('ix_activities_type'), 'activities', ['type'], unique=False)
    op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_activities_project_id'), 'activities', ['project_id'], unique=False)
    op.create_index(op.f('ix_activities_location'), 'activities', ['location'], unique=False)
    op.create_index(op.f('ix_activities_created_at'), 'activities', ['created_at'], unique=False)
    
    # Create composite indexes for better query performance
    op.create_index('idx_activities_user_project_created', 'activities', ['user_id', 'project_id', 'created_at'], unique=False)
    op.create_index('idx_activities_type_created', 'activities', ['type', 'created_at'], unique=False)
    op.create_index('idx_activities_location_created', 'activities', ['location', 'created_at'], unique=False)

    # Create user_presence table
    op.create_table('user_presence',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_location', sa.String(length=500), nullable=True),
        sa.Column('current_activity', sa.String(length=50), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('session_started', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_presence_id'), 'user_presence', ['id'], unique=False)
    op.create_index(op.f('ix_user_presence_user_id'), 'user_presence', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_presence_project_id'), 'user_presence', ['project_id'], unique=False)
    op.create_index(op.f('ix_user_presence_session_id'), 'user_presence', ['session_id'], unique=False)
    op.create_index(op.f('ix_user_presence_last_seen'), 'user_presence', ['last_seen'], unique=False)
    
    # Create composite indexes for presence queries
    op.create_index('idx_user_presence_user_project', 'user_presence', ['user_id', 'project_id'], unique=False)
    op.create_index('idx_user_presence_status_last_seen', 'user_presence', ['status', 'last_seen'], unique=False)

    # Create activity_summaries table
    op.create_table('activity_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('summary_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('activity_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_active_time_seconds', sa.String(length=20), nullable=False),
        sa.Column('first_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locations_worked', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('collaborations_count', sa.String(length=10), nullable=False),
        sa.Column('conflicts_detected', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_summaries_id'), 'activity_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_activity_summaries_user_id'), 'activity_summaries', ['user_id'], unique=False)
    op.create_index(op.f('ix_activity_summaries_project_id'), 'activity_summaries', ['project_id'], unique=False)
    op.create_index(op.f('ix_activity_summaries_summary_date'), 'activity_summaries', ['summary_date'], unique=False)
    
    # Create composite index for summary queries
    op.create_index('idx_activity_summaries_user_date', 'activity_summaries', ['user_id', 'summary_date'], unique=False)


def downgrade() -> None:
    # Drop activity_summaries table
    op.drop_index('idx_activity_summaries_user_date', table_name='activity_summaries')
    op.drop_index(op.f('ix_activity_summaries_summary_date'), table_name='activity_summaries')
    op.drop_index(op.f('ix_activity_summaries_project_id'), table_name='activity_summaries')
    op.drop_index(op.f('ix_activity_summaries_user_id'), table_name='activity_summaries')
    op.drop_index(op.f('ix_activity_summaries_id'), table_name='activity_summaries')
    op.drop_table('activity_summaries')

    # Drop user_presence table
    op.drop_index('idx_user_presence_status_last_seen', table_name='user_presence')
    op.drop_index('idx_user_presence_user_project', table_name='user_presence')
    op.drop_index(op.f('ix_user_presence_last_seen'), table_name='user_presence')
    op.drop_index(op.f('ix_user_presence_session_id'), table_name='user_presence')
    op.drop_index(op.f('ix_user_presence_project_id'), table_name='user_presence')
    op.drop_index(op.f('ix_user_presence_user_id'), table_name='user_presence')
    op.drop_index(op.f('ix_user_presence_id'), table_name='user_presence')
    op.drop_table('user_presence')

    # Drop activities table
    op.drop_index('idx_activities_location_created', table_name='activities')
    op.drop_index('idx_activities_type_created', table_name='activities')
    op.drop_index('idx_activities_user_project_created', table_name='activities')
    op.drop_index(op.f('ix_activities_created_at'), table_name='activities')
    op.drop_index(op.f('ix_activities_location'), table_name='activities')
    op.drop_index(op.f('ix_activities_project_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_user_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_type'), table_name='activities')
    op.drop_index(op.f('ix_activities_id'), table_name='activities')
    op.drop_table('activities')