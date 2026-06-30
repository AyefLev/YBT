# Server Package

The server package is the non-Docker distribution layer for the existing FastAPI
backend and worker.

## Responsibilities

- Start API service.
- Start worker service.
- Read production config from an external file.
- Run database migrations and bootstrap commands.
- Provide health checks and log locations.

## Production Dependencies

Recommended production dependencies:

- PostgreSQL 16
- Redis 7
- Qdrant 1.12+
- File storage on local disk, NAS, MinIO, or S3-compatible object storage

## First Milestone

Create scripts for:

- `ybt-server start-api`
- `ybt-server start-worker`
- `ybt-server migrate`
- `ybt-server bootstrap-admin`
- `ybt-server health`

These commands can initially wrap the existing backend package and later become
a proper executable distribution.
