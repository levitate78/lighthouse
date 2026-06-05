# REST API & Code Reference

## API Endpoints

| Method | Path                                   | Description                                                     |
|--------|----------------------------------------|-----------------------------------------------------------------|
| GET    | `/api/projects`                        | Fetch authorized projects. Optional query param: `branch`.     |
| GET    | `/api/projects/:id/pipelines`          | Fetch pipelines for project. Optional query param: `branch`.    |
| GET    | `/api/pipelines/:id/jobs`              | Fetch cached jobs for a specific pipeline.                      |
| GET    | `/api/summary`                         | Get summary statistics.                                         |
| POST   | `/api/sync`                            | Trigger foreground and background synchronization.             |
| GET    | `/api/sync/status`                     | Check progress of active synchronization tasks.                  |

---

## Python Code Reference

### GitLab Utility Functions

::: gitlab_utils
    options:
      show_root_heading: true
