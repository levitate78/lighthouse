import app


def test_create_app_registers_blueprints(app):
    assert "api" in app.blueprints
    assert "auth" in app.blueprints
    assert app.testing is True
