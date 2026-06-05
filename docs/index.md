# LIGHTHOUSE Documentation

Welcome to the **LIGHTHOUSE** documentation. LIGHTHOUSE provides a platform for visualising and cached-browsing GitLab CI/CD pipelines.

## Purpose

The application:
- Syncs GitLab pipeline data and stores it in a local database (SQLite in development, PostgreSQL in production).
- Provides a fast, premium web interface to filter, browse, and audit pipeline results.
- Spawns background threads/workers to sync older pipeline histories, avoiding direct GitLab API query limitations.

## Features

- **Summary Dashboard**: View pass/fail metrics and filter projects instantly.
- **Microservices-ready architecture**: Decoupled backend and frontend, designed with states stored entirely in the database (`sync_progress`).
- **Interactive UI**: Search projects by name/namespace, filter by branch name across all projects, and check sync progress in real time.
- **Admin Panel**: Manage user registrations, approvals, and authorization.
