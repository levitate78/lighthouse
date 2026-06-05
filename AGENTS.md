# AGENTS.md

# Project Overview

The project is a web application designed to interact with the GitLab API, reading pipeline information, storing in a local database and providing dashboarding capability of pipeline/job information.

This repository contains:

- Python backend
- HTML templates
- CSS styling
- JavaScript frontend logic
- Automated tests
- CI/CD deployment pipeline

When making changes, prefer minimal, targeted modifications over broad refactors.
---

# Development Principles

## General

- Understand the existing implementation before modifying it.
- Preserve existing behavior unless the task explicitly requires changing it.
- Do not rewrite working code without a clear reason.
- Prefer consistency with existing patterns over introducing new frameworks or styles.
- Avoid speculative improvements.
- Keep pull requests focused on the requested task.
- Ensure any changes work across deployment architectures including Docker Compose and Kubernetes.

## Code Quality

- Prioritize readability over cleverness.
- Use descriptive variable and function names.
- Avoid excessive abstraction.
- Remove dead code when encountered.
- Avoid introducing global state.

---

# Repository Structure

## Backend

Backend code is located in:

- backend/

Primary language:

- Python 3.12+

## Frontend

Frontend code is located in:

- frontend/

Technologies:

- HTML
- CSS
- JavaScript

## Tests

Tests are located in:

- backend/tests/

---

# Files and Directories To Ignore

Unless explicitly requested, do not read, modify, or generate files within:

- __pycache__/
- .ruff_cache/
- .venv/
- backend/__pycache__/
- backend/.ruff_cache/
- backend/.venv/
- backend/.vscode/
- backend/instance/
- backend/.pdm-python
- backend/pdm.lock
- frontend/node_modules
- node_modules/
- .venv/
- venv/
- build/
- dist/
- coverage/
- .pytest_cache/
- .mypy_cache/
- .ruff_cache/
- __pycache__/

Do not modify:

- package-lock.json
- yarn.lock
- pnpm-lock.yaml
- poetry.lock

unless dependency changes are required.

Avoid editing generated files.

---

# Python Guidelines

## Style

- Follow PEP 8.
- Use type hints where appropriate.
- Prefer pathlib over os.path for new code.
- Prefer f-strings over string concatenation.
- Prefer single quotes over double quotes.
- Ensure Ruff standards are adhered to.

## Imports

- Standard library imports first.
- Third-party imports second.
- Local imports last.

## Functions

- Keep functions focused on a single responsibility.
- Prefer small functions over large functions.
- Extract duplicated logic when duplication is meaningful.

## Error Handling

- Handle expected exceptions explicitly.
- Do not use bare `except:`.
- Log errors when appropriate.
- Do not silently suppress exceptions.

## Dependencies

Before introducing a new dependency:

1. Check whether the functionality already exists.
2. Prefer standard library solutions.
3. Justify the dependency in comments or documentation.

---

# HTML Guidelines

## Templates

- Preserve existing template structure.
- Reuse existing components and partials.
- Keep markup semantic.

Use:

- header
- nav
- main
- section
- article
- footer

when appropriate.

## Accessibility

Maintain accessibility standards:

- Use proper labels.
- Use semantic elements.
- Ensure keyboard accessibility.
- Preserve ARIA attributes.
- Preserve alt text.

---

# CSS Guidelines

## Styling

- Follow existing CSS architecture.
- Reuse existing utility classes.
- Avoid inline styles.

## Changes

- Make the smallest styling change necessary.
- Do not introduce new design systems.
- Do not change spacing, typography, or colors globally unless requested.

## Responsive Design

Ensure changes work on:

- Mobile
- Tablet
- Desktop

---

# JavaScript Guidelines

## General

- Prefer modern JavaScript.
- Avoid introducing frameworks unless already used.
- Use existing project conventions.

## DOM Manipulation

- Minimize unnecessary DOM updates.
- Avoid duplicate event listeners.
- Clean up listeners when appropriate.

## Network Requests

- Reuse existing API helpers.
- Handle loading and error states.
- Validate responses.

---

# Security Requirements

- ALWAYS highlight any identified security vulnerabilities, and propose fixes to resolve issues.
- NEVER introduce known or potential vulnerabilities into the codebase.

## Never

- Expose secrets.
- Hardcode credentials.
- Log passwords.
- Log authentication tokens.
- Disable security checks.

## Input Validation

Treat all user input as untrusted.

Validate:

- Query parameters
- Form inputs
- JSON payloads
- Uploaded files

## Authentication

Preserve existing authentication and authorization behavior unless explicitly requested.

---

# Database Rules

If database migrations are required:

- Generate only the migration necessary for the requested change.
- Do not modify historical migrations.
- Preserve backward compatibility where possible.

Avoid:

- Destructive schema changes
- Large data migrations

unless explicitly requested.

---

# API Changes

When modifying APIs:

- Maintain backwards compatibility whenever possible.
- Update tests.
- Update documentation.
- Preserve response formats.

---

# Testing Requirements

After making changes:

1. Run relevant tests.
2. Run linting.
3. Verify no obvious regressions.

Minimum commands:

```bash
pytest
ruff check .
```

If frontend changes are made, also run:

```bash
npm test
```

if available.

---

# Documentation

Update documentation when:

- Behavior changes
- APIs change
- Configuration changes
- New environment variables are added

Relevant files:

- README.md
- docs/

---

# Git Guidelines

Keep commits focused.

Avoid:

- Unrelated formatting changes
- Repository-wide refactors
- Renaming files unnecessarily

---

# Decision Priority

When instructions conflict, follow this order:

1. Direct user request
2. More specific AGENTS.md instructions
3. Repository conventions
4. General best practices

---

# Expected Agent Behaviour

Before making changes:

1. Read only files relevant to the task.
2. Understand the current implementation.
3. Identify the smallest safe change.
4. Update tests if needed.
5. Verify consistency with surrounding code.

When uncertain:

- Ask for clarification rather than guessing.

Prefer correctness over speed.
Prefer minimal changes over large refactors.
