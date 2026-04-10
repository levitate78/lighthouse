"""Pytest configuration and shared fixtures for the LIGHTHOUSE backend tests."""

import os

# All required environment variables must be set BEFORE importing the app
# because config.py validates them at import time.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("GLT_SECRET_KEY", "test-glt-secret-key-for-ci")
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
    test_app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            # Use in-memory SQLite for fast, isolated tests.
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with test_app.app_context():
        # Create all tables directly — Alembic is not used for tests.
        db.create_all()
        yield test_app


@pytest.fixture(autouse=True)
def cleanup_db(app):
    """Roll back and truncate all tables after every test."""
    yield
    db.session.rollback()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
