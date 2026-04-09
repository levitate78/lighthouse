import api

from extensions import db
from models import Project, User, UserSelectedGroup


def test_get_authorized_project_group_ids(monkeypatch):
    dummy_user = type(
        "DummyUser",
        (),
        {"selected_groups": [type("G", (), {"group_id": 1})(), type("G", (), {"group_id": None})()]},
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
