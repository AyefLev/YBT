# Desktop Client

Technology: Tauri 2 + existing Vue frontend.

## Responsibilities

- Host the existing web UI in a native application shell.
- Let users configure the institution server URL.
- Store local client settings.
- Open downloads and exported documents through the OS.
- Avoid storing institution data locally.

## Current Layout

This desktop project does not duplicate the frontend source. It references the
existing `../../frontend` project:

```text
desktop/
  src-tauri/
  package.json
```

During development, Tauri starts the existing Vite dev server on
`http://127.0.0.1:1420`.

During desktop build, Tauri first runs the existing frontend build and bundles
`../../frontend/dist`.

## API Base URL Strategy

The current frontend should be adjusted so API calls can use:

1. a configured desktop server URL;
2. the current web origin when running in browser mode;
3. a dev proxy during local development.

The client should store the selected server URL in the OS app config directory.

In the first desktop milestone, the server URL is stored through the existing
frontend local-storage layer. A later milestone can move it to Tauri's native
app config directory.

## Prerequisites

- Node.js 20+
- npm
- Rust toolchain with Cargo
- Tauri system dependencies for the target operating system

This machine currently has Node/npm but not Rust/Cargo, so the project files can
be prepared here while actual Tauri builds require installing Rust first.

## Commands

```powershell
npm install
npm run dev
npm run build
```

`npm run dev` launches the desktop shell and the existing frontend dev server.
`npm run build` builds the existing frontend and then creates desktop bundles.

For a clean local-tooling workflow from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File release/tools/install-desktop-deps.ps1
powershell -ExecutionPolicy Bypass -File release/tools/setup-rust-portable.ps1
powershell -ExecutionPolicy Bypass -File release/tools/desktop-build.ps1
```

The first successful Windows build produced:

```text
release/desktop/src-tauri/target/release/ybt-desktop.exe
release/desktop/src-tauri/target/release/bundle/msi/Yanbeitong AI_0.1.0_x64_en-US.msi
release/desktop/src-tauri/target/release/bundle/nsis/Yanbeitong AI_0.1.0_x64-setup.exe
```

The system-level product name is currently `Yanbeitong AI` because WiX MSI's
default code page cannot bundle Chinese product names without custom
localization. The app UI itself still displays the Chinese product name from the
frontend.
