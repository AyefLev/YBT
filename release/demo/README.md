# Local Demo Bundle

The local demo bundle is a convenience package for presentation and offline
evaluation. It is not the recommended production deployment.

## Goals

- Run on one machine.
- Seed demo users and teaching data.
- Avoid requiring Docker during presentation.
- Keep production security boundaries clear.

## Possible Runtime Choices

- SQLite for business data.
- Local file storage under the demo data directory.
- LanceDB or local Qdrant process for vector search.
- In-process task queue for simple asynchronous jobs.

## Warning

Local demo mode must not be marketed as the institution deployment mode. It is
for demonstration, trial, and development only.
