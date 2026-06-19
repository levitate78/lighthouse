# Architecture & Microservices

LIGHTHOUSE is built with a decoupled architecture that is prepared for containerization and Kubernetes scaling.

```text
+-------------------+
|     Nginx/Vite    | (Frontend SPA - Vanilla JS)
+---------+---------+
          | Proxy /api/*
+---------v---------+
|     Flask App     | (REST API & Core Application)
+----+---------+----+
     |         |
     |         +-------------------+
     |                             |
+----v----+                  +-----v-----+
| SQLite/ |                  | Scalable  | (Background sync workers)
| Postgres| (Shared DB state) | Workers   | (Reads/writes progress to DB)
+---------+                  +-----------+
```

## Backend Services

The backend is built with Python and Flask. Database interactions use **Flask-SQLAlchemy** for ORM mapping.

- **Main Application**: Handles REST API requests, user auth, and serving the single-page HTML.
- **Worker Services (APScheduler)**: Performs synchronization with GitLab APIs.

### Microservice & Kubernetes Scalability

To support a true microservice architecture in Kubernetes:
1. **Core Application**: A lightweight deployment handling API requests and serving static assets.
2. **Scalable Worker Nodes**: Distinct pods running background sync processes.
3. **Database-centric Synchronization**: All background tasks update their progress (projects completed, pipelines synced) inside the shared `sync_progress` table in the PostgreSQL database.
4. **Real-time Status Fetching**: The core application polls this table to update the frontend summary bar, ensuring correct status representation even if tasks run on external pods/nodes.

## Frontend SPA

The frontend uses Vite for bundling, vanilla ES modules, and plain CSS with modern styling (dark theme, glassmorphism, pulse animations).

All state is maintained in a single state object in `frontend/js/app.js`, triggering targeted DOM mutations in `frontend/js/render.js`.

## Template Architecture (Development vs Production)

This project uses **two separate HTML templates** to support different deployment modes:

### Development Mode
- **File**: `backend/templates/index.html`
- **Rendered by**: Flask (`@app.route("/")``)
- **Contains**: Jinja2 template directives for:
  - Injecting Vite dev server URLs (for hot module replacement)
  - Inserting CSRF token as `<meta>` tag
  - Conditional asset loading based on `VITE_DEV_SERVER` environment variable

### Production Mode
- **File**: `frontend/index.html`
- **Served by**: Nginx (static file at `/static/dist/index.html`)
- **Built by**: Vite (pre-compiled with hashed asset filenames)
- **CSRF token**: Fetched via `/api/csrf-token` endpoint instead of meta tag

### Critical Sync Requirement

These two templates **must be kept in sync**. When you update HTML structure (navigation, element IDs, layout, modals, etc.):

1. **Update `frontend/index.html` first** (source of truth)
2. **Replicate the changes to `backend/templates/index.html`**
3. **Verify element IDs and CSS classes match exactly**
4. **Test in both development and production modes**

**Why this matters**: Features can work in production but break in development (or vice versa) if templates diverge. The JavaScript relies on stable element IDs (`main-panel`, `metrics-page-btn`, etc.) that must exist in both versions.

### When Templates Can Differ

Only Jinja2-specific code should differ between the files:
- Asset loading conditionals (`{% if vite_dev %}`)
- CSRF token injection
- Vite helper functions (`{{ vite_asset() }}`, `{{ vite_css() }}`)

**All HTML structure and IDs must be identical.**
