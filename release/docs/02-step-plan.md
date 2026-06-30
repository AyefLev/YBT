# Step Plan

## Step 1: Release Workspace Skeleton

Status: done.

Outputs:

- Independent `YBT-Release` workspace.
- C/S architecture decision.
- Runtime mode definitions.
- Initial packaging manifest.

## Step 2: Desktop Client Skeleton

Status: in progress.

Goal:

- Create `desktop/` as a Tauri client.
- Reuse the existing Vue UI as the client frontend.
- Add first-run server URL configuration.
- Store API base URL locally.

Acceptance:

- Desktop app opens a login screen.
- User can configure `http://localhost:8080` or a remote server.
- API calls use the configured base URL.

Current outputs:

- Tauri 2 skeleton under `release/desktop/`.
- Desktop dev/build scripts reference the existing `YBT/frontend` project.
- Frontend API client supports a runtime server URL while preserving browser
  relative API behavior.
- Login page exposes server connection settings.
- Backend exposes configurable CORS origins for desktop clients.
- Local tooling scripts under `release/tools/` keep Rust/Cargo and desktop npm
  dependencies inside the repository working area.

Open requirement:

- Install Rust/Cargo before running `npm run dev` or `npm run build` in
  `desktop/`.

## Step 3: Server Distribution Layer

Goal:

- Add non-Docker server startup scripts.
- Define production config file format.
- Add bootstrap admin command.
- Add migration and health-check command.

Acceptance:

- Server can start without Docker when dependencies are available.
- Config lives outside source code.
- Logs and data paths are predictable.

## Step 4: Installer Strategy

Goal:

- Windows desktop installer.
- Server zip package or service installer.
- GitHub Release artifact layout.

Acceptance:

- Release contains desktop client and server package.
- Version number is visible in client and server.
- Upgrade notes are generated.

## Step 5: Local Demo Bundle

Goal:

- One-machine demo package.
- Uses local storage and demo seed data.
- Useful for classroom presentation and evaluation.

Acceptance:

- Demo can run without institutional server.
- Demo mode is labeled in config and docs.
- Production docs still recommend C/S deployment.
