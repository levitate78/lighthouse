from auth import load_user
from extensions import db
from models import User


def test_load_user_returns_none_for_unknown_user(app):
    with app.app_context():
        assert load_user(999999) is None


def test_load_user_returns_existing_user(app):
    with app.app_context():
        user = User(
            username="authuser",
            name="Auth User",
            email="auth@example.com",
            provider="local",
            password_hash="hash",
        )
        db.session.add(user)
        db.session.commit()

        loaded = load_user(user.id)
        assert loaded is not None
        assert loaded.id == user.id
