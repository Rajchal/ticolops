"""Add notification models

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('action_text', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('channels', sa.JSON(), nullable=False),
        sa.Column('delivery_attempts', sa.Integer(), nullable=False),
        sa.Column('last_delivery_attempt', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_project_id'), 'notifications', ['project_id'], unique=False)
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'], unique=False)
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_notifications_read_at'), 'notifications', ['read_at'], unique=False)

    # Create notification_preferences table
    op.create_table('notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False),
        sa.Column('email_address', sa.String(length=255), nullable=True),
        sa.Column('email_frequency', sa.String(length=20), nullable=False),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=False),
        sa.Column('webhook_enabled', sa.Boolean(), nullable=False),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('slack_enabled', sa.Boolean(), nullable=False),
        sa.Column('slack_webhook_url', sa.String(length=500), nullable=True),
        sa.Column('slack_channel', sa.String(length=100), nullable=True),
        sa.Column('type_preferences', sa.JSON(), nullable=False),
        sa.Column('project_preferences', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_notification_preferences_id'), 'notification_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=True)

    # Create notification_delivery_logs table
    op.create_table('notification_delivery_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_delivery_logs_id'), 'notification_delivery_logs', ['id'], unique=False)
    op.create_index(op.f('ix_notification_delivery_logs_notification_id'), 'notification_delivery_logs', ['notification_id'], unique=False)
    op.create_index(op.f('ix_notification_delivery_logs_channel'), 'notification_delivery_logs', ['channel'], unique=False)
    op.create_index(op.f('ix_notification_delivery_logs_status'), 'notification_delivery_logs', ['status'], unique=False)

    # Create notification_subscriptions table
    op.create_table('notification_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('notification_types', sa.JSON(), nullable=False),
        sa.Column('channels', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('auto_subscribed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_subscriptions_id'), 'notification_subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_notification_subscriptions_user_id'), 'notification_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_notification_subscriptions_topic'), 'notification_subscriptions', ['topic'], unique=False)

    # Create notification_templates table
    op.create_table('notification_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('subject_template', sa.String(length=255), nullable=True),
        sa.Column('title_template', sa.String(length=255), nullable=False),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_templates_id'), 'notification_templates', ['id'], unique=False)
    op.create_index(op.f('ix_notification_templates_type'), 'notification_templates', ['type'], unique=False)
    op.create_index(op.f('ix_notification_templates_channel'), 'notification_templates', ['channel'], unique=False)

    # Create notification_digests table
    op.create_table('notification_digests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('digest_type', sa.String(length=20), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('notification_count', sa.Integer(), nullable=False),
        sa.Column('notifications', sa.JSON(), nullable=False),
        sa.Column('summary_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_digests_id'), 'notification_digests', ['id'], unique=False)
    op.create_index(op.f('ix_notification_digests_user_id'), 'notification_digests', ['user_id'], unique=False)
    op.create_index(op.f('ix_notification_digests_digest_type'), 'notification_digests', ['digest_type'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_notification_digests_digest_type'), table_name='notification_digests')
    op.drop_index(op.f('ix_notification_digests_user_id'), table_name='notification_digests')
    op.drop_index(op.f('ix_notification_digests_id'), table_name='notification_digests')
    op.drop_table('notification_digests')
    
    op.drop_index(op.f('ix_notification_templates_channel'), table_name='notification_templates')
    op.drop_index(op.f('ix_notification_templates_type'), table_name='notification_templates')
    op.drop_index(op.f('ix_notification_templates_id'), table_name='notification_templates')
    op.drop_table('notification_templates')
    
    op.drop_index(op.f('ix_notification_subscriptions_topic'), table_name='notification_subscriptions')
    op.drop_index(op.f('ix_notification_subscriptions_user_id'), table_name='notification_subscriptions')
    op.drop_index(op.f('ix_notification_subscriptions_id'), table_name='notification_subscriptions')
    op.drop_table('notification_subscriptions')
    
    op.drop_index(op.f('ix_notification_delivery_logs_status'), table_name='notification_delivery_logs')
    op.drop_index(op.f('ix_notification_delivery_logs_channel'), table_name='notification_delivery_logs')
    op.drop_index(op.f('ix_notification_delivery_logs_notification_id'), table_name='notification_delivery_logs')
    op.drop_index(op.f('ix_notification_delivery_logs_id'), table_name='notification_delivery_logs')
    op.drop_table('notification_delivery_logs')
    
    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_index(op.f('ix_notification_preferences_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')
    
    op.drop_index(op.f('ix_notifications_read_at'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_created_at'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_project_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')