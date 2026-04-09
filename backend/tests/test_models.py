from datetime import datetime, timezone

from extensions import db
from models import Pipeline, PipelineJob, Project, User, UserSelectedGroup


def test_user_to_dict():
    user = User(
        id=1,
        username="test",
        name="Test User",
        email="test@example.com",
        avatar_url="https://example.com/avatar.png",
        provider="local",
        approved=True,
    )
    data = user.to_dict()
    assert data["id"] == 1
    assert data["username"] == "test"
    assert data["approved"] is True


def test_user_selected_group_to_dict():
    group = UserSelectedGroup(
        id=1,
        user_id=1,
        group_id=123,
        group_name="Test Group",
        group_full_path="namespace/test-group",
    )
    data = group.to_dict()
    assert data["group_id"] == 123
    assert data["group_full_path"] == "namespace/test-group"


def test_pipeline_job_to_dict():
    job = PipelineJob(
        id=10,
        pipeline_id=1,
        name="build",
        stage="test",
        status="success",
        web_url="https://gitlab.example.com/job/10",
        duration=12.5,
    )
    data = job.to_dict()
    assert data["id"] == 10
    assert data["status"] == "success"


def test_project_to_dict_includes_latest_pipeline(app):
    with app.app_context():
        project = Project(id=1, group_id=123, name="Awesome Project")
        db.session.add(project)
        pipeline = Pipeline(
            id=100,
            project_id=1,
            ref="main",
            sha="abcdef1234567890",
            status="success",
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(pipeline)
        db.session.commit()

        result = project.to_dict()
        assert result["id"] == 1
        assert result["latest_pipeline"]["id"] == 100
