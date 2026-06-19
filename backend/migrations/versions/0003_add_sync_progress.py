"""Add sync progress table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_progress",
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("group_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("total_projects", sa.Integer(), nullable=True),
        sa.Column("current_project", sa.Integer(), nullable=True),
        sa.Column("total_pipelines", sa.Integer(), nullable=True),
        sa.Column("current_pipeline", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=512), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("group_id")
    )


def downgrade() -> None:
    op.drop_table("sync_progress")
