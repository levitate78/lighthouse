import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GITLAB_URL", "https://gitlab.example.com")
os.environ.setdefault("FLASK_DEBUG", "false")

import sys

sys.path.insert(0, "..")

import pytest

import app as app_module
from extensions import db

# Prevent the scheduler from starting during tests.
app_module.scheduler.start = lambda *args, **kwargs: None


@pytest.fixture(scope="session")
def app():
    test_app = app_module.create_app()
    test_app.config.update({"TESTING": True, "WTF_CSRF_ENABLED": False})
    with test_app.app_context():
        yield test_app


@pytest.fixture(autouse=True)
def cleanup_db(app):
    yield
    with app.app_context():
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
