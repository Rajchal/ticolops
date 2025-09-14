"""Add deployment models

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Create deployments table
    op.create_table('deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commit_sha', sa.String(length=40), nullable=False),
        sa.Column('branch', sa.String(length=255), nullable=False),
        sa.Column('trigger', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('project_type', sa.String(length=50), nullable=False),
        sa.Column('build_config', sa.JSON(), nullable=True),
        sa.Column('environment_variables', sa.JSON(), nullable=True),
        sa.Column('preview_url', sa.String(length=500), nullable=True),
        sa.Column('build_logs', sa.Text(), nullable=True),
        sa.Column('deployment_logs', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('build_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('deployment_duration_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployments_id'), 'deployments', ['id'], unique=False)
    op.create_index(op.f('ix_deployments_repository_id'), 'deployments', ['repository_id'], unique=False)
    op.create_index(op.f('ix_deployments_project_id'), 'deployments', ['project_id'], unique=False)
    op.create_index(op.f('ix_deployments_status'), 'deployments', ['status'], unique=False)
    op.create_index(op.f('ix_deployments_created_at'), 'deployments', ['created_at'], unique=False)

    # Create deployment_environments table
    op.create_table('deployment_environments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('subdomain_pattern', sa.String(length=255), nullable=True),
        sa.Column('environment_variables', sa.JSON(), nullable=True),
        sa.Column('build_command', sa.String(length=500), nullable=True),
        sa.Column('output_directory', sa.String(length=255), nullable=True),
        sa.Column('auto_deploy_branches', sa.JSON(), nullable=True),
        sa.Column('require_approval', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployment_environments_id'), 'deployment_environments', ['id'], unique=False)
    op.create_index(op.f('ix_deployment_environments_project_id'), 'deployment_environments', ['project_id'], unique=False)

    # Create build_configurations table
    op.create_table('build_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('build_command', sa.String(length=500), nullable=False),
        sa.Column('output_directory', sa.String(length=255), nullable=False),
        sa.Column('install_command', sa.String(length=500), nullable=True),
        sa.Column('detection_files', sa.JSON(), nullable=True),
        sa.Column('detection_patterns', sa.JSON(), nullable=True),
        sa.Column('default_env_vars', sa.JSON(), nullable=True),
        sa.Column('framework_version', sa.String(length=50), nullable=True),
        sa.Column('node_version', sa.String(length=20), nullable=True),
        sa.Column('python_version', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_build_configurations_id'), 'build_configurations', ['id'], unique=False)
    op.create_index(op.f('ix_build_configurations_project_type'), 'build_configurations', ['project_type'], unique=False)

    # Create deployment_hooks table
    op.create_table('deployment_hooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hook_type', sa.String(length=50), nullable=False),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('working_directory', sa.String(length=255), nullable=True),
        sa.Column('executed', sa.Boolean(), nullable=False),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error_output', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployment_hooks_id'), 'deployment_hooks', ['id'], unique=False)
    op.create_index(op.f('ix_deployment_hooks_deployment_id'), 'deployment_hooks', ['deployment_id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_deployment_hooks_deployment_id'), table_name='deployment_hooks')
    op.drop_index(op.f('ix_deployment_hooks_id'), table_name='deployment_hooks')
    op.drop_table('deployment_hooks')
    
    op.drop_index(op.f('ix_build_configurations_project_type'), table_name='build_configurations')
    op.drop_index(op.f('ix_build_configurations_id'), table_name='build_configurations')
    op.drop_table('build_configurations')
    
    op.drop_index(op.f('ix_deployment_environments_project_id'), table_name='deployment_environments')
    op.drop_index(op.f('ix_deployment_environments_id'), table_name='deployment_environments')
    op.drop_table('deployment_environments')
    
    op.drop_index(op.f('ix_deployments_created_at'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_status'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_project_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_repository_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_id'), table_name='deployments')
    op.drop_table('deployments')