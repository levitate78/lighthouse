# LIGHTHOUSE

LIGHTHOUSE provides a platform for visualising GitLab CI pipelines. View the status, interrogate results across groups, and understand where your codebase is at.

A lightweight Python/Flask web application to monitor the status of all GitLab
CI/CD pipelines within a group of projects. Pipelines are synced from the GitLab
API on a configurable schedule and cached in a local database for fast, offline
browsing.

---

## Architecture

```
gitlab-pipeline-monitor/
├── app.py                   # Flask app — REST API, Vite manifest helper, scheduler
├── config.py                # Configuration (reads from .env)
├── models.py                # SQLAlchemy ORM: Project, Pipeline, PipelineJob
├── gitlab_client.py         # GitLab API v4 wrapper with pagination
│
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
│
├── static/
│   └── dist/                # Vite build output (gitignored)
│       ├── assets/          # Hashed JS + CSS bundles
│       └── .vite/
│           └── manifest.json
│
├── templates/
│   └── index.html           # Pure HTML skeleton; Vite assets injected by Jinja2
│
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
python app.py
# → http://localhost:5000  (open this in your browser)
```

The Flask template detects `VITE_DEV_SERVER` and loads JS/CSS from Vite's
dev server, giving you full HMR while hitting the real Flask API.

### Production

```bash
# 1. Build the frontend — outputs hashed bundles to static/dist/
cd frontend && npm run build

# 2. Unset VITE_DEV_SERVER in .env (or remove the line entirely)

# 3. Run Flask (or Gunicorn)
python app.py
# or: gunicorn -w 2 "app:app"
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

---

## REST API

| Method | Path                                   | Description                    |
|--------|----------------------------------------|--------------------------------|
| GET    | `/api/projects`                        | All projects + latest pipeline |
| GET    | `/api/projects/:id/pipelines?limit=15` | Recent pipelines for a project |
| GET    | `/api/pipelines/:id/jobs`              | Jobs for a specific pipeline   |
| GET    | `/api/summary`                         | Aggregate status counts        |
| POST   | `/api/sync`                            | Trigger an immediate sync      |

---

## Production notes

- **PostgreSQL**: set `DATABASE_URL` to `postgresql+psycopg2://user:pass@host/db`
  and uncomment `psycopg2-binary` in `requirements.txt`
- **Gunicorn**: use `-w 2` max to avoid duplicate APScheduler instances; or
  replace APScheduler with a dedicated Celery + Redis worker
- **Static files**: point Nginx at `static/dist/` so it serves assets directly —
  Flask doesn't need to be in that path at all
- **Cache headers**: Vite's hashed filenames are safe to cache forever with
  `Cache-Control: max-age=31536000, immutable`
- **`static/dist/` in `.gitignore`**: commit the source in `frontend/src/`,
  not the build output; regenerate it in CI