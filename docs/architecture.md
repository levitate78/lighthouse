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
