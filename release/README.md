# YBT Release Engineering

This workspace contains the release-oriented engineering layer for Yanbeitong AI.
It is intentionally separated from the current web/service codebase so desktop
packaging, server installers, migration scripts, and release notes can evolve
without disturbing day-to-day feature development.

## Goal

Build Yanbeitong AI as an installable C/S product:

- Desktop client: installed by teachers, students, teaching managers, and admins.
- Server package: deployed by an institution and owns business data.
- Local demo package: optional offline demonstration bundle for presentations.

## Recommended Runtime Shape

```text
YBT Desktop Client
        |
        | HTTPS / API
        v
YBT Server
        |
        +-- PostgreSQL: users, roles, courses, classes, assignments, logs
        +-- Redis: cache, async task state, rate limits
        +-- Qdrant: institution knowledge vector index
        +-- File storage: uploaded materials, exports, generated artifacts
```

The desktop client should not own core business data. It only stores local
settings, login state, and small UI caches. This keeps collaboration, auditing,
backup, and permission boundaries on the server.

## Folder Map

```text
YBT/release/
  README.md
  docs/
    01-target-architecture.md
    02-step-plan.md
    03-runtime-modes.md
  desktop/
    README.md
  server/
    README.md
  demo/
    README.md
  packaging/
    release-manifest.example.yml
```

## Current Step

Step 1 creates the release-engineering skeleton and locks the architectural
direction. The next step is to create a Tauri desktop client that can connect to
the existing server through a configurable API base URL.

## Local Tooling

Tooling that is expensive or easy to pollute system state should stay under
`release/`:

- `release/desktop/node_modules` for desktop npm dependencies.
- `release/.toolchains/rustup` and `release/.toolchains/cargo` for local Rust.

Use scripts under `release/tools/` to install or activate those dependencies.
