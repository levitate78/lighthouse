import api
from datetime import datetime, timezone

from extensions import db
from models import Pipeline, PipelineJob, Project, User, UserSelectedGroup


def test_get_authorized_project_group_ids(monkeypatch):
    dummy_user = type(
        "DummyUser",
        (),
        {
            "selected_groups": [
                type("G", (), {"group_id": 1})(),
                type("G", (), {"group_id": None})(),
            ]
        },
    )
    monkeypatch.setattr(api, "current_user", dummy_user)

    assert api._get_authorized_project_group_ids() == [1]


def test_api_projects_filters_by_selected_groups(app, monkeypatch):
    with app.app_context():
        user = User(
            username="tester",
            name="Tester",
            email="tester@example.com",
            provider="local",
            password_hash="hash",
        )
        db.session.add(user)
        db.session.commit()

        selected_group = UserSelectedGroup(
            user_id=user.id,
            group_id=123,
            group_name="Test Group",
            group_full_path="test/group",
        )
        db.session.add(selected_group)

        visible_project = Project(id=1, group_id=123, name="Visible Project")
        hidden_project = Project(id=2, group_id=999, name="Hidden Project")
        db.session.add_all([visible_project, hidden_project])
        db.session.commit()

        monkeypatch.setattr(api, "current_user", user)

        with app.test_request_context("/api/projects?page=1&per_page=10"):
            response = api.api_projects.__wrapped__()

        assert response.json["total"] == 1
        assert response.json["projects"][0]["id"] == 1


def test_api_job_metrics_aggregates_authorized_project_data(app, monkeypatch):
    with app.app_context():
        user = User(
            username="metrics",
            name="Metrics User",
            email="metrics@example.com",
            provider="local",
            password_hash="hash",
        )
        db.session.add(user)
        db.session.commit()

        db.session.add(
            UserSelectedGroup(
                user_id=user.id,
                group_id=123,
                group_name="Metrics Group",
                group_full_path="metrics/group",
            )
        )
        project = Project(id=10, group_id=123, name="Visible Project")
        hidden_project = Project(id=11, group_id=999, name="Hidden Project")
        db.session.add_all([project, hidden_project])

        pipeline = Pipeline(
            id=100,
            project_id=10,
            ref="main",
            status="success",
            created_at=datetime.now(timezone.utc),
            coverage=87.5,
            test_total=12,
            test_success=11,
            test_failed=1,
        )
        hidden_pipeline = Pipeline(
            id=101,
            project_id=11,
            ref="main",
            status="failed",
            created_at=datetime.now(timezone.utc),
        )
        db.session.add_all([pipeline, hidden_pipeline])
        db.session.add_all(
            [
                PipelineJob(
                    id=1000,
                    pipeline_id=100,
                    name="test",
                    status="success",
                    duration=20,
                ),
                PipelineJob(
                    id=1001,
                    pipeline_id=100,
                    name="test",
                    status="failed",
                    duration=40,
                ),
                PipelineJob(
                    id=1002,
                    pipeline_id=101,
                    name="hidden",
                    status="failed",
                    duration=90,
                ),
            ]
        )
        db.session.commit()

        monkeypatch.setattr(api, "current_user", user)

        with app.test_request_context("/api/job-metrics?days=30"):
            response = api.api_job_metrics.__wrapped__()

        assert response.json["summary"]["job_count"] == 2
        assert response.json["summary"]["pipeline_count"] == 1
        assert response.json["summary"]["job_status_counts"] == {
            "failed": 1,
            "success": 1,
        }
        assert response.json["summary"]["duration"]["avg"] == 30
        assert response.json["summary"]["duration"]["min"] == 20
        assert response.json["summary"]["duration"]["max"] == 40
        assert response.json["summary"]["coverage_avg"] == 87.5
        assert response.json["summary"]["tests"]["total"] == 12
        assert response.json["summary"]["tests"]["failed"] == 1
