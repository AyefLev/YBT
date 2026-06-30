# Local Tooling

Release tooling is designed to stay inside `release/` so it can be removed
without touching the user's system environment.

## Layout

```text
release/
  .toolchains/
    rustup/
    cargo/
  desktop/
    node_modules/
```

## Rust

Use `setup-rust-portable.ps1` to install Rust through rustup with:

- `RUSTUP_HOME=release/.toolchains/rustup`
- `CARGO_HOME=release/.toolchains/cargo`
- `--no-modify-path`

This keeps Rust and Cargo data local to the release workspace.

## Desktop Dependencies

Use `install-desktop-deps.ps1` to install desktop npm dependencies under
`release/desktop/node_modules`.

## Cleanup

Run:

```powershell
powershell -ExecutionPolicy Bypass -File release/tools/clean-local-tooling.ps1
```

This removes:

- `release/.toolchains`
- `release/desktop/node_modules`
- `release/desktop/src-tauri/target`
