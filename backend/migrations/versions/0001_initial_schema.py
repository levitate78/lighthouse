"""Initial schema — create all tables.

Revision ID: 0001
Revises:
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ───────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gitlab_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("gitlab_token", sa.String(length=255), nullable=True),
        sa.Column("password_change_required", sa.Boolean(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gitlab_id"),
        sa.UniqueConstraint("username"),
    )

    # ── user_selected_groups ────────────────────────────────────────────────
    op.create_table(
        "user_selected_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("group_name", sa.String(length=255), nullable=False),
        sa.Column("group_full_path", sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── projects ────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("namespace", sa.String(length=512), nullable=True),
        sa.Column("web_url", sa.String(length=1024), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_group_id", "projects", ["group_id"], unique=False)

    # ── pipelines ───────────────────────────────────────────────────────────
    op.create_table(
        "pipelines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(length=512), nullable=True),
        sa.Column("sha", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("web_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("queued_duration", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipelines_project_id", "pipelines", ["project_id"], unique=False)
    op.create_index(
        "ix_pipelines_project_created",
        "pipelines",
        ["project_id", "created_at"],
        unique=False,
    )

    # ── pipeline_jobs ───────────────────────────────────────────────────────
    op.create_table(
        "pipeline_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pipeline_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("stage", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("web_url", sa.String(length=1024), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runner_name", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["pipelines.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_jobs_pipeline_id", "pipeline_jobs", ["pipeline_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_jobs_pipeline_id", table_name="pipeline_jobs")
    op.drop_table("pipeline_jobs")

    op.drop_index("ix_pipelines_project_created", table_name="pipelines")
    op.drop_index("ix_pipelines_project_id", table_name="pipelines")
    op.drop_table("pipelines")

    op.drop_index("ix_projects_group_id", table_name="projects")
    op.drop_table("projects")

    op.drop_table("user_selected_groups")
    op.drop_table("users")