# Deployment

LIGHTHOUSE supports multiple deployment modes — from local development with
SQLite to production-grade Docker Compose and Kubernetes clusters.

---

## Docker Compose (recommended)

The repository ships a ready-to-use `docker-compose.yml` that orchestrates
three services:

| Service     | Image / Build              | Purpose                                  |
|-------------|----------------------------|------------------------------------------|
| **db**      | `postgres:16-alpine`       | Persistent PostgreSQL database           |
| **backend** | `./backend/Dockerfile`     | Flask API server with Gunicorn           |
| **frontend**| `./frontend/Dockerfile`    | Nginx serving the Vite-built SPA         |

### Quick start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/lighthouse.git
cd lighthouse

# 2. Create your environment file
cp .env.example .env
# Edit .env and set at minimum:
#   SECRET_KEY, GLT_SECRET_KEY, POSTGRES_PASSWORD,
#   GITLAB_URL, GITLAB_TOKEN

# 3. Build and run
docker compose up --build -d

# 4. Verify all services are healthy
docker compose ps
```

The frontend is exposed on port **80** by default (configurable via
`HTTP_PORT` in `.env`).

### Stopping / rebuilding

```bash
# Stop
docker compose down

# Full rebuild (e.g. after code changes)
docker compose up --build -d
```

---

## Environment configuration

All configuration is managed through environment variables. Copy
`.env.example` to `.env` and adjust the values.

### Required variables

| Variable             | Description                                           |
|----------------------|-------------------------------------------------------|
| `SECRET_KEY`         | Flask session signing key                             |
| `GLT_SECRET_KEY`     | Fernet key for encrypting stored GitLab tokens        |
| `POSTGRES_PASSWORD`  | Password for the PostgreSQL `lighthouse` user         |
| `GITLAB_URL`         | GitLab instance URL (e.g. `https://gitlab.com`)       |
| `GITLAB_TOKEN`       | GitLab PAT with `read_api` scope (for scheduled sync) |

### Optional variables

| Variable                      | Default                          | Description                                  |
|-------------------------------|----------------------------------|----------------------------------------------|
| `FIRST_ADMIN_PASSWORD`        | *(must set on first run)*        | Initial password for the `admin` user        |
| `DATABASE_URL`                | `sqlite:///pipeline_monitor.db`  | SQLAlchemy connection string                 |
| `SYNC_INTERVAL_SECONDS`       | `60`                             | Seconds between scheduled GitLab syncs       |
| `SCHEDULER_ENABLED`           | `0`                              | Set to `1` on exactly one process/pod        |
| `HTTP_PORT`                   | `80`                             | Host port exposed by the frontend container  |
| `GITLAB_OAUTH_CLIENT_ID`      | *(blank)*                        | GitLab OAuth app ID for SSO login            |
| `GITLAB_OAUTH_CLIENT_SECRET`  | *(blank)*                        | GitLab OAuth app secret                      |
| `ENABLE_GITLAB_LOGIN`         | `true`                           | Show "Login with GitLab" option              |
| `SESSION_COOKIE_SECURE`       | `false`                          | Set to `true` behind HTTPS                   |
| `VITE_DEV_SERVER`             | *(blank)*                        | Vite dev server URL (development only)       |

---

## Database migrations

Migrations are managed with **Alembic** and run automatically on container
startup via the backend entrypoint script. To run them manually:

```bash
# Inside the backend container
docker compose exec backend flask init-db

# Or run alembic directly
docker compose exec backend alembic upgrade head
```

---

## Kubernetes deployment

LIGHTHOUSE is designed with Kubernetes scaling in mind. The architecture
separates concerns so that different components can scale independently.

### Target architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster                                              │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │  Ingress /   │   │  Core App    │   │  Worker Deployment   │ │
│  │  Nginx       │──▶│  Deployment  │   │  (N replicas)        │ │
│  │              │   │  (API only)  │   │                      │ │
│  └──────────────┘   └──────┬───────┘   └──────────┬───────────┘ │
│                            │                      │              │
│                     ┌──────▼──────────────────────▼────────┐     │
│                     │        PostgreSQL (StatefulSet        │     │
│                     │            or managed RDS)            │     │
│                     └─────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### Deployment strategy

1. **Core Application** — A `Deployment` running the Flask API server.
   Set `SCHEDULER_ENABLED=0` so this pod only serves HTTP requests.

2. **Worker Nodes** — A separate `Deployment` (or `CronJob`) running the
   sync process. Set `SCHEDULER_ENABLED=1` on exactly one replica. Workers
   write their progress to the shared `sync_progress` database table, which
   the core application reads via `/api/sync/status`.

3. **Database** — A PostgreSQL `StatefulSet` or managed database service
   (e.g. AWS RDS, GCP Cloud SQL). All services connect via `DATABASE_URL`.

4. **Frontend** — The Nginx container serving the Vite-built SPA. Deploy
   behind an `Ingress` resource with TLS termination.

### Key configuration for K8s

| Env Variable         | Core App | Worker | Notes                                            |
|----------------------|----------|--------|--------------------------------------------------|
| `SCHEDULER_ENABLED`  | `0`      | `1`    | Only the worker should run scheduled syncs       |
| `DATABASE_URL`       | shared   | shared | Both must point to the same PostgreSQL instance  |
| `SECRET_KEY`         | shared   | shared | Must match across all pods for session validity  |
| `GLT_SECRET_KEY`     | shared   | shared | Must match for token encryption/decryption       |

### Health checks

The backend exposes `GET /api/health` which returns `{"status": "ok"}`.
Use this for Kubernetes liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /api/health
    port: 5000
  initialDelaySeconds: 15
  periodSeconds: 30
readinessProbe:
  httpGet:
    path: /api/health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## Local development (without Docker)

For local development without containers, see the [README](../README.md)
quick start section — run the Vite dev server and Flask backend in two
separate terminals.
