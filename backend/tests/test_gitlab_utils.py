import gitlab

from gitlab_utils import get_gitlab_client, validate_gitlab_token


def test_get_gitlab_client_uses_config(app, monkeypatch):
    class DummyClient:
        def __init__(self, url, private_token=None):
            self.url = url
            self.private_token = private_token

    monkeypatch.setattr(gitlab, "Gitlab", DummyClient)

    with app.app_context():
        client = get_gitlab_client(private_token="secret-token")
        assert isinstance(client, DummyClient)
        assert client.url == app.config["GITLAB_URL"]
        assert client.private_token == "secret-token"


def test_validate_gitlab_token_rejects_short_tokens(app):
    with app.test_request_context():
        valid, message = validate_gitlab_token("short")
        assert valid is False
        assert "too short" in message


def test_validate_gitlab_token_handles_http_statuses(app, monkeypatch):
    class DummyResponse:
        status_code = 401
        text = "Unauthorized"

    def fake_get(url, headers, timeout):
        assert url.startswith(app.config["GITLAB_URL"])
        assert headers["PRIVATE-TOKEN"] == "valid-token"
        return DummyResponse()

    monkeypatch.setattr("gitlab_utils.requests.get", fake_get)

    with app.test_request_context():
        valid, message = validate_gitlab_token("valid-token")
        assert valid is False
        assert "invalid or expired token" in message
