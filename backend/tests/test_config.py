import os

from config import Config


def test_config_loads_secret_key():
    assert Config.SECRET_KEY == os.environ["SECRET_KEY"]
    assert Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite://")
    assert isinstance(Config.ENABLE_GITLAB_LOGIN, bool)
