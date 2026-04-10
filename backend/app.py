"""
LIGHTHOUSE — Flask Application
"""

import os
import json
import logging
import secrets
from datetime import datetime, timezone

from flask import Flask, render_template, jsonify
from flask_login import login_required
from flask_dance.contrib.gitlab import make_gitlab_blueprint
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash

from config import Config
from extensions import db, scheduler, login_manager, limiter, cors
from auth import auth_bp, load_user
from api import api_bp
from models import User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["WTF_CSRF_ENABLED"] = True

    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    scheduler.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    csrf = CSRFProtect(app)  # noqa: F841
    login_manager.login_view = "auth.login"
    login_manager.user_loader(load_user)

    gitlab_bp = make_gitlab_blueprint(
        client_id=app.config["GITLAB_OAUTH_CLIENT_ID"],
        client_secret=app.config["GITLAB_OAUTH_CLIENT_SECRET"],
        hostname=app.config["GITLAB_URL"],
        redirect_to="gitlab_login",
    )

    app.register_blueprint(gitlab_bp, url_prefix="/login")
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    # ── Security headers ───────────────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # ── Main SPA route ─────────────────────────────────────────────────────
    # In development Flask renders the Jinja2 template which injects Vite
    # asset URLs and the CSRF token meta tag.
    # In production the pre-built SPA is served directly by nginx; the SPA
    # fetches /api/csrf-token on boot instead.
    @app.route("/")
    @login_required
    def index():
        return render_template("index.html")

    # ── Vite asset helpers ─────────────────────────────────────────────────
    def _load_vite_manifest() -> dict:
        manifest_path = os.path.join(
            app.static_folder, "dist", ".vite", "manifest.json"
        )
        if not os.path.exists(manifest_path):
            manifest_path = os.path.join(app.static_folder, "dist", "manifest.json")
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except FileNotFoundError:
            app.logger.warning(
                "Vite manifest not found — run `npm run build` inside frontend/"
            )
            return {}

    @app.context_processor
    def vite_assets():
        vite_dev = app.config.get("VITE_DEV_SERVER", "")

        def vite_asset(name: str) -> str:
            if vite_dev:
                return f"{vite_dev.rstrip('/')}/{name}"
            manifest = _load_vite_manifest()
            entry = manifest.get(name, {})
            file_path = entry.get("file", name)
            return f"/static/dist/{file_path}"

        def vite_css(name: str) -> str:
            if vite_dev:
                return ""
            manifest = _load_vite_manifest()
            css_files = manifest.get(name, {}).get("css", [])
            return "\n".join(
                f'<link rel="stylesheet" href="/static/dist/{css}">'
                for css in css_files
            )

        return dict(vite_asset=vite_asset, vite_css=vite_css, vite_dev=vite_dev)

    # ── Database initialisation ────────────────────────────────────────────
    # db.create_all() is intentionally NOT called here; use:
    #   - `alembic upgrade head`  in production / Docker (run by entrypoint.sh)
    #   - `flask init-db`         for local development without Docker
    #   - conftest.py             calls db.create_all() directly for tests
    with app.app_context():
        _seed_admin_user(app)

    # ── Background scheduler ───────────────────────────────────────────────
    scheduler.add_job(
        id="sync_pipelines",
        func="sync:sync_pipelines_background",
        trigger="interval",
        seconds=app.config.get("SYNC_INTERVAL_SECONDS", 60),
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()

    return app


def _seed_admin_user(app: Flask) -> None:
    """Create a default admin account if no users exist yet."""
    try:
        if not User.query.first():
            admin_password = secrets.token_urlsafe(16)
            admin_user = User(
                username="admin",
                name="Administrator",
                email="admin@localhost",
                password_hash=generate_password_hash(admin_password),
                provider="local",
                password_change_required=True,
                approved=True,
                is_admin=True,
            )
            db.session.add(admin_user)
            db.session.commit()
            app.logger.warning(
                'Admin user created with username "admin" and password: %s. '
                "Please change this password after first login.",
                admin_password,
            )
            print(f"\nAdmin user created with password: {admin_password}")
            print("Please change the password after first login.\n")
    except Exception:
        # Tables may not exist yet (first run before migrations).
        # The entrypoint will run alembic upgrade head before starting gunicorn,
        # so this is a no-op during container startup sequencing.
        db.session.rollback()


# ── CLI helpers ────────────────────────────────────────────────────────────

app = create_app()


@app.cli.command("init-db")
def init_db_command():
    """Initialise the database for local development (non-Docker).

    For production use `alembic upgrade head` instead.
    """
    db.create_all()
    _seed_admin_user(app)
    print("Database tables created.")


if __name__ == "__main__":
    debug = app.config.get("DEBUG", False)
    app.run(
        debug=debug,
        use_reloader=debug,
        host=app.config.get("HOST", "127.0.0.1"),
        port=app.config.get("PORT", 5000),
    )