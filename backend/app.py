"""
LIGHTHOUSE — Flask Application
"""

import os
import fcntl
import logging
from datetime import datetime, timezone

from flask import Flask, render_template
from flask_login import login_required
from flask_dance.contrib.gitlab import make_gitlab_blueprint
from flask_wtf import CSRFProtect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from config import Config
from extensions import db, scheduler, login_manager, limiter, cors
from auth import auth_bp, load_user
from api import api_bp
from models import User


_scheduler_lock_fd = None

logging.basicConfig(level=logging.DEBUG,format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.debug('Logging successfully configured.')

def _acquire_scheduler_lock() -> bool:
    """Acquire a non-blocking file lock so only one process runs the scheduler."""
    global _scheduler_lock_fd

    if _scheduler_lock_fd is not None:
        return True

    lock_path = os.environ.get("SCHEDULER_LOCK_FILE", "/tmp/lighthouse_scheduler.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)

    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(lock_fd)
        return False

    _scheduler_lock_fd = lock_fd
    return True


def _should_start_scheduler() -> bool:
    """Return True only for the designated process that should run APScheduler."""
    scheduler_enabled = os.environ.get("SCHEDULER_ENABLED") == "1"
    is_werkzeug_main = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    is_flask_cli_command = (
        os.environ.get("FLASK_RUN_FROM_CLI") == "true" and not is_werkzeug_main
    )

    if is_flask_cli_command:
        return False

    should_run = scheduler_enabled or is_werkzeug_main
    if not should_run:
        return False

    return _acquire_scheduler_lock()


def create_app():
    logger.debug('Creating App')
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["WTF_CSRF_ENABLED"] = True

    db.init_app(app)
    scheduler_was_running = scheduler.running
    if not scheduler_was_running:
        scheduler.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    csrf = CSRFProtect(app)  # noqa: F841
    login_manager.login_view = "auth.login"
    login_manager.user_loader(load_user)
    logger.debug('Creating GitLab Blueprint')
    gitlab_bp = make_gitlab_blueprint(
        client_id=app.config["GITLAB_OAUTH_CLIENT_ID"],
        client_secret=app.config["GITLAB_OAUTH_CLIENT_SECRET"],
        hostname=app.config["GITLAB_URL"],
        redirect_to="gitlab_login",
    )
    logger.debug('Registering Blueprints')
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
    @app.context_processor
    def vite_assets():
        vite_dev = app.config.get("VITE_DEV_SERVER", "")
        entry_to_asset = {
            "js/main.js": "assets/main.js",
            "js/auth.js": "assets/auth.js",
        }
        entry_to_css = {
            "js/main.js": "assets/main.css",
            "js/auth.js": "assets/auth.css",
        }

        def vite_asset(name: str) -> str:
            if vite_dev:
                return f"{vite_dev.rstrip('/')}/{name}"
            return f"/static/dist/{entry_to_asset.get(name, name)}"

        def vite_css(name: str) -> str:
            if vite_dev:
                return ""
            css_file = entry_to_css.get(name)
            if not css_file:
                return ""
            return f'<link rel="stylesheet" href="/static/dist/{css_file}">'

        return dict(vite_asset=vite_asset, vite_css=vite_css, vite_dev=vite_dev)

    # ── Database initialisation ────────────────────────────────────────────
    # db.create_all() is intentionally NOT called here; use:
    #   - `alembic upgrade head`  in production / Docker (run by entrypoint.sh)
    #   - `flask init-db`         for local development without Docker
    #   - conftest.py             calls db.create_all() directly for tests
    with app.app_context():
        if _should_seed():
            logger.debug('Checking admin user status...')
            _seed_admin_user(app)

    # ── Background scheduler ───────────────────────────────────────────────
    if not scheduler_was_running:
        scheduler.add_job(
            id="sync_pipelines",
            func="sync:sync_pipelines_background",
            trigger="interval",
            seconds=app.config.get("SYNC_INTERVAL_SECONDS", 60),
            next_run_time=datetime.now(timezone.utc),
            replace_existing=True,
        )
        if _should_start_scheduler():
            scheduler.start()

    return app

def _should_seed():
    return _acquire_scheduler_lock()

def _seed_admin_user(app: Flask) -> None:
    """Create a default admin account if no users exist yet."""
    try:
        existing_admin = User.query.filter_by(username="admin")
        admin_password = os.getenv("FIRST_ADMIN_PASSWORD")
        if existing_admin:
            logger.debug('Admin user found; not creating')
        admin_password = os.getenv('FIRST_ADMIN_PASSWORD')
        if not admin_password:
            raise KeyError(
                "Environment variable FIRST_ADMIN_PASSWORD must be set to create the initial admin user."
            )
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
        logger.debug('Admin user created.')
    except Exception as e:
        # Tables may not exist yet (first run before migrations).
        # The entrypoint will run alembic upgrade head before starting gunicorn,
        # so this is a no-op during container startup sequencing.
        db.session.rollback()
        logger.error(e)


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
