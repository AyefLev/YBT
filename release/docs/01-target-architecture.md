# Target Architecture

## Product Form

Yanbeitong AI should be released as a client/server product rather than a pure
single-machine application.

```text
Desktop Client                         Institution Server
---------------                        ------------------
Tauri shell                            FastAPI API service
Vue UI                                 Worker service
Local settings                         PostgreSQL
Token/session cache                    Redis
Optional offline cache                 Qdrant
                                        File storage
                                        Model/API provider config
```

## Why C/S

The system includes shared teaching and administrative data:

- Users, roles, teacher approval, and permission boundaries.
- Courses, chapters, classes, assignments, submissions, and grading.
- Public teaching resources and institution knowledge bases.
- Model provider keys, token usage, audit logs, and operations data.
- Multi-role workflows involving teachers, students, managers, and admins.

Those concerns should live on a trusted server. A desktop client can provide a
better installation and migration experience, but it should remain a client.

## Component Responsibilities

### Desktop Client

- Renders the Vue application in a native desktop shell.
- Stores server URL, theme/user preferences, and login token.
- Talks to the server through HTTPS APIs.
- Can later support optional local draft cache.
- Does not store institution-wide courses, classes, assignments, or API keys.

### Server Package

- Runs the FastAPI backend and worker.
- Owns database migrations and bootstrap admin creation.
- Manages PostgreSQL, Redis, Qdrant, and file storage configuration.
- Provides health checks, logs, backup/export commands, and upgrade scripts.

### Local Demo Package

- Used for offline presentation and smoke testing.
- May use SQLite and embedded/local vector storage.
- Should be clearly separated from production deployment.

## Data Boundary

```text
Client local:
  - server_url
  - access token / refresh state
  - non-sensitive UI preferences
  - optional unsaved draft cache

Server:
  - users and roles
  - courses, classes, assignments, questions
  - uploaded materials and exports
  - vector indexes
  - token usage and billing estimates
  - model provider configs and secrets
```

## Security Boundary

- Admin and model API keys remain server-only.
- The desktop client should never receive provider secrets.
- All permission decisions must be enforced by backend APIs.
- Client-side visibility is convenience only, not authorization.
