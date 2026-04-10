"""Use BIGINT for GitLab-derived identifiers.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-10 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "gitlab_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )

    with op.batch_alter_table("user_selected_groups") as batch_op:
        batch_op.alter_column(
            "group_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "group_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )

    with op.batch_alter_table("pipelines") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table("pipeline_jobs") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "pipeline_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("pipeline_jobs") as batch_op:
        batch_op.alter_column(
            "pipeline_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table("pipelines") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column(
            "group_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table("user_selected_groups") as batch_op:
        batch_op.alter_column(
            "group_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "gitlab_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
