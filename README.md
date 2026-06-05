# LIGHTHOUSE

LIGHTHOUSE provides a platform for visualising GitLab CI pipelines. View the status, interrogate results across groups, and understand where your codebase is at.

A lightweight Python/Flask web application to monitor the status of all GitLab
CI/CD pipelines within a group of projects. Pipelines are synced from the GitLab
API on a configurable schedule and cached in a local database for fast, offline
browsing.

---

## Architecture

```text
gitlab-pipeline-monitor/
├── backend/
│   ├── app.py               # Flask app — REST API, Vite manifest helper, scheduler
│   ├── config.py            # Configuration (reads from .env)
│   ├── models.py            # SQLAlchemy ORM: User, Project, Pipeline, PipelineJob
│   ├── gitlab_utils.py      # GitLab API helper with token encryption
│   ├── pyproject.toml
│   ├── templates/
│   │   └── index.html       # Pure HTML skeleton; Vite assets injected by Jinja2
│   └── static/
│       └── dist/            # Vite build output (gitignored)
│           ├── assets/      # Hashed JS + CSS bundles
│           └── .vite/
│               └── manifest.json
├── frontend/                # Vite project root
│   ├── package.json
│   ├── vite.config.js       # Outputs to ../static/dist/ with manifest
│   └── src/
│       ├── css/
│       │   └── main.css     # All styles, design tokens, components
│       └── js/
│           ├── main.js      # Vite entry point (imports CSS + app)
│           ├── utils.js     # Pure helpers — formatters, esc(), shimmer
│           ├── api.js       # All fetch() calls to the Flask REST API
│           ├── render.js    # All DOM construction and mutation
│           └── app.js       # State, event wiring, boot sequence
├── requirements.txt
└── .env.example
```

### Backend stack

| Component        | Library                                         |
|------------------|-------------------------------------------------|
| Web framework    | Flask 3                                         |
| ORM / database   | Flask-SQLAlchemy + SQLite (dev) / PostgreSQL (prod) |
| Background sync  | Flask-APScheduler                               |
| GitLab API       | `requests`                                      |

### Frontend stack

| Component        | Tool                                            |
|------------------|-------------------------------------------------|
| Build tool       | Vite 5                                          |
| Language         | Vanilla ES modules                              |
| Styles           | Plain CSS with custom properties                |
| Fonts            | IBM Plex Mono + IBM Plex Sans (Google Fonts)    |

---

## Quick start

### 1. Python backend

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Fill in GITLAB_TOKEN and GITLAB_GROUP_ID
```

### 2. Frontend

```bash
cd frontend
npm install
```

---

## Running

### Docker Compose (recommended)

The simplest way to run LIGHTHOUSE in production is via Docker Compose.
The included `docker-compose.yml` orchestrates three services: PostgreSQL,
the Flask backend, and an Nginx frontend.

```bash
# 1. Copy and configure environment variables
cp .env.example .env
# Edit .env — set SECRET_KEY, GLT_SECRET_KEY, POSTGRES_PASSWORD,
#             GITLAB_URL, and GITLAB_TOKEN at minimum

# 2. Build and start all services
docker compose up --build -d

# 3. Verify everything is healthy
docker compose ps
```

The application is exposed on port **80** by default (set `HTTP_PORT` in
`.env` to change). Database migrations run automatically on startup.

To tear down:
```bash
docker compose down          # stop containers (data persists)
docker compose down -v       # stop and remove volumes
```

### Development (two terminals)

**Terminal 1 — Vite dev server** (hot module replacement):
```bash
cd frontend
npm run dev
# → http://localhost:5173 (proxies /api/* to Flask)
```

**Terminal 2 — Flask**:
```bash
# Ensure VITE_DEV_SERVER=http://localhost:5173 is set in .env
python backend/app.py
# → http://localhost:5000  (open this in your browser)
```

The Flask template detects `VITE_DEV_SERVER` and loads JS/CSS from Vite's
dev server, giving you full HMR while hitting the real Flask API.

### Manual production build

```bash
# 1. Build the frontend — outputs hashed bundles to static/dist/
cd frontend && npm run build

# 2. Unset VITE_DEV_SERVER in .env (or remove the line entirely)

# 3. Run Flask (or Gunicorn)
python backend/app.py
# or: gunicorn -w 2 "backend.app:app"
```

Flask reads `static/dist/.vite/manifest.json` to inject the correct hashed
filenames into `templates/index.html` at request time.

---

## Configuration

| Variable                | Description                                      | Default                         |
|-------------------------|--------------------------------------------------|---------------------------------|
| `GITLAB_URL`            | GitLab instance URL                              | `https://gitlab.com`            |
| `GITLAB_TOKEN`          | Personal/project access token (`read_api` scope) | *(required)*                    |
| `GITLAB_GROUP_ID`       | Group ID or URL-encoded path                     | *(required)*                    |
| `DATABASE_URL`          | SQLAlchemy DB URI                                | `sqlite:///pipeline_monitor.db` |
| `SYNC_INTERVAL_SECONDS` | GitLab poll interval                             | `60`                            |
| `VITE_DEV_SERVER`       | Vite dev server URL (dev only, blank in prod)    | *(blank)*                       |
| `SECRET_KEY`            | Flask secret key                                 | *(change in production)*        |
| `SCHEDULER_ENABLED`     | Enable scheduler startup (`1`) for scheduler-capable processes | `0`                             |
| `SCHEDULER_LOCK_FILE`   | File path used for inter-process scheduler lock    | `/tmp/lighthouse_scheduler.lock`|

---

## REST API

| Method | Path                                   | Description                                  |
|--------|----------------------------------------|----------------------------------------------|
| GET    | `/api/health`                          | Liveness probe (unauthenticated)             |
| GET    | `/api/projects?branch=`                | All projects + latest pipeline; filter by branch |
| GET    | `/api/projects/:id/pipelines?limit=&branch=` | Recent pipelines for a project; filter by branch |
| GET    | `/api/pipelines/:id/jobs`              | Jobs for a specific pipeline                 |
| GET    | `/api/summary`                         | Aggregate status counts                      |
| POST   | `/api/sync`                            | Trigger foreground + background sync         |
| GET    | `/api/sync/status`                     | Active sync progress for authorized groups   |

---

## Production notes

- **PostgreSQL**: set `DATABASE_URL` to `postgresql+psycopg2://user:pass@host/db`
  and uncomment `psycopg2-binary` in `requirements.txt`
- **Gunicorn / scheduler**: set `SCHEDULER_ENABLED=1` on exactly one process
  (or one dedicated dyno/pod) so only scheduler-capable processes attempt
  startup. A file lock (`SCHEDULER_LOCK_FILE`) ensures only one process actually
  starts `sync_pipelines` even with multiple Gunicorn workers. Flask debug/CLI
  parent processes are ignored unless the Werkzeug reloader child is active
  (`WERKZEUG_RUN_MAIN=true`).
- **Static files**: point Nginx at `static/dist/` so it serves assets directly —
  Flask doesn't need to be in that path at all
- **Cache headers**: Vite's hashed filenames are safe to cache forever with
  `Cache-Control: max-age=31536000, immutable`
- **`static/dist/` in `.gitignore`**: commit the source in `frontend/src/`,
  not the build output; regenerate it in CI

---

## Documentation

Full documentation (architecture, API reference, and deployment guides) is
built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material "mkdocstrings[python]"

# Build the static documentation site
mkdocs build

# Or serve locally with live reload
mkdocs serve
# → http://localhost:8000
```

Documentation source lives in `docs/` and configuration is in `mkdocs.yml`.