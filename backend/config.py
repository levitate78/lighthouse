"""
Application configuration — reads from environment variables.
Copy .env.example to .env and fill in your values before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Validate required environment variables
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY environment variable is required and cannot be empty"
        )

    # GitLab token encryption key (REQUIRED)
    GLT_SECRET_KEY = os.getenv("GLT_SECRET_KEY")
    if not GLT_SECRET_KEY:
        raise ValueError(
            "GLT_SECRET_KEY environment variable is required and cannot be empty"
        )

    # Database — SQLite by default, swap for PostgreSQL in production:
    #   postgresql+psycopg2://user:password@host/dbname
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///pipeline_monitor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # GitLab
    GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
    GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")  # Personal / project access token
    GITLAB_GROUP_ID = os.getenv("GITLAB_GROUP_ID", "")  # Group ID or URL-encoded path

    # Sync interval in seconds (default: 60)
    try:
        SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
        if SYNC_INTERVAL_SECONDS <= 0:
            raise ValueError("SYNC_INTERVAL_SECONDS must be a positive integer")
    except ValueError:
        raise ValueError("SYNC_INTERVAL_SECONDS must be a positive integer")

    # Vite dev server URL — set this when running `npm run dev` locally.
    # Leave blank in production (assets are served from static/dist/).
    VITE_DEV_SERVER = os.getenv("VITE_DEV_SERVER", "")

    # GitLab OAuth
    GITLAB_OAUTH_CLIENT_ID = os.getenv("GITLAB_OAUTH_CLIENT_ID", "")
    GITLAB_OAUTH_CLIENT_SECRET = os.getenv("GITLAB_OAUTH_CLIENT_SECRET", "")

    # Login configuration
    ENABLE_GITLAB_LOGIN = os.getenv("ENABLE_GITLAB_LOGIN", "true").lower() == "true"

    # Session security
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # APScheduler
    SCHEDULER_API_ENABLED = False
