"""Add cached pipeline and job metrics.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-05 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pipelines") as batch_op:
        batch_op.add_column(sa.Column("coverage", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("test_total", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("test_success", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("test_failed", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("test_skipped", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("test_error", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("test_duration", sa.Float(), nullable=True))

    with op.batch_alter_table("pipeline_jobs") as batch_op:
        batch_op.add_column(sa.Column("coverage", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("pipeline_jobs") as batch_op:
        batch_op.drop_column("coverage")

    with op.batch_alter_table("pipelines") as batch_op:
        batch_op.drop_column("test_duration")
        batch_op.drop_column("test_error")
        batch_op.drop_column("test_skipped")
        batch_op.drop_column("test_failed")
        batch_op.drop_column("test_success")
        batch_op.drop_column("test_total")
        batch_op.drop_column("coverage")
