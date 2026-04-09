"""
Database models for LIGHTHOUSE.
"""

from datetime import datetime, timezone

from extensions import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(
        db.Integer, unique=True, nullable=True
    )  # Only for GitLab users
    username = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(1024), default="")
    provider = db.Column(db.String(50), default="local")  # 'gitlab' or 'local'
    password_hash = db.Column(db.String(255), nullable=True)  # Only for local users
    gitlab_token = db.Column(db.String(255), nullable=True)  # GitLab PAT for API access
    password_change_required = db.Column(db.Boolean, default=False)  # For admin user
    approved = db.Column(db.Boolean, default=True)  # Approval status for new users
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Selected groups for monitoring
    selected_groups = db.relationship(
        "UserSelectedGroup", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def gitlab_token_decrypted(self):
        if self.gitlab_token:
            from gitlab_utils import decrypt_token
            return decrypt_token(self.gitlab_token)
        return None

    @gitlab_token_decrypted.setter
    def gitlab_token_decrypted(self, value):
        if value:
            from gitlab_utils import encrypt_token
            self.gitlab_token = encrypt_token(value)
        else:
            self.gitlab_token = None
        return {
            "id": self.id,
            "gitlab_id": self.gitlab_id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "provider": self.provider,
            "has_gitlab_token": bool(
                self.gitlab_token
            ),  # Don't expose the actual token
            "approved": self.approved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSelectedGroup(db.Model):
    __tablename__ = "user_selected_groups"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    group_id = db.Column(db.Integer, nullable=False)  # GitLab group ID
    group_name = db.Column(db.String(255), nullable=False)
    group_full_path = db.Column(db.String(512), nullable=False)

    user = db.relationship("User", back_populates="selected_groups")

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "group_full_path": self.group_full_path,
        }


class Project(db.Model):
    __tablename__ = "projects"
    __table_args__ = (db.Index("ix_projects_group_id", "group_id"),)

    id = db.Column(db.Integer, primary_key=True)  # GitLab project ID
    group_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(255), nullable=False)
    namespace = db.Column(db.String(512), default="")
    web_url = db.Column(db.String(1024), default="")
    default_branch = db.Column(db.String(255), default="main")
    last_synced_at = db.Column(db.DateTime(timezone=True))

    pipelines = db.relationship(
        "Pipeline",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def latest_pipeline(self):
        return self.pipelines.order_by(Pipeline.created_at.desc()).first()

    def to_dict(self):
        latest = self.latest_pipeline()
        return {
            "id": self.id,
            "name": self.name,
            "namespace": self.namespace,
            "web_url": self.web_url,
            "default_branch": self.default_branch,
            "last_synced_at": self.last_synced_at.isoformat()
            if self.last_synced_at
            else None,
            "latest_pipeline": latest.to_dict() if latest else None,
        }


class Pipeline(db.Model):
    __tablename__ = "pipelines"

    id = db.Column(db.Integer, primary_key=True)  # GitLab pipeline ID
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    ref = db.Column(db.String(512), default="")
    sha = db.Column(db.String(64), default="")
    status = db.Column(db.String(64), default="unknown")
    source = db.Column(db.String(128), default="")
    web_url = db.Column(db.String(1024), default="")
    created_at = db.Column(db.DateTime(timezone=True))
    updated_at = db.Column(db.DateTime(timezone=True))
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    duration = db.Column(db.Float, nullable=True)
    queued_duration = db.Column(db.Float, nullable=True)

    project = db.relationship("Project", back_populates="pipelines")
    jobs = db.relationship(
        "PipelineJob", back_populates="pipeline", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "ref": self.ref,
            "sha": self.sha[:8] if self.sha else "",
            "status": self.status,
            "source": self.source,
            "web_url": self.web_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration": self.duration,
            "queued_duration": self.queued_duration,
        }


class PipelineJob(db.Model):
    __tablename__ = "pipeline_jobs"

    id = db.Column(db.Integer, primary_key=True)  # GitLab job ID
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"), nullable=False)
    name = db.Column(db.String(255), default="")
    stage = db.Column(db.String(255), default="")
    status = db.Column(db.String(64), default="unknown")
    web_url = db.Column(db.String(1024), default="")
    duration = db.Column(db.Float, nullable=True)
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    runner_name = db.Column(db.String(512), default="")

    pipeline = db.relationship("Pipeline", back_populates="jobs")

    def to_dict(self):
        return {
            "id": self.id,
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "stage": self.stage,
            "status": self.status,
            "web_url": self.web_url,
            "duration": self.duration,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "runner_name": self.runner_name,
        }
