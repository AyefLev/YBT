$ErrorActionPreference = "Stop"

$releaseRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$rustupHome = Join-Path $releaseRoot ".toolchains\rustup"
$cargoHome = Join-Path $releaseRoot ".toolchains\cargo"
$cargoBin = Join-Path $cargoHome "bin"

if (-not (Test-Path $cargoBin)) {
    throw "Local Rust toolchain not found. Run release/tools/setup-rust-portable.ps1 first."
}

$env:RUSTUP_HOME = $rustupHome
$env:CARGO_HOME = $cargoHome
$env:Path = "$cargoBin;$env:Path"

Write-Host "Local Rust enabled for this PowerShell process."
rustc --version
cargo --version
