param(
    [string]$Toolchain = "stable"
)

$ErrorActionPreference = "Stop"

$releaseRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$toolchainRoot = Join-Path $releaseRoot ".toolchains"
$rustupHome = Join-Path $toolchainRoot "rustup"
$cargoHome = Join-Path $toolchainRoot "cargo"
$downloadDir = Join-Path $toolchainRoot "downloads"
$rustupInit = Join-Path $downloadDir "rustup-init.exe"
$rustupUrl = "https://win.rustup.rs/x86_64"

New-Item -ItemType Directory -Force -Path $rustupHome, $cargoHome, $downloadDir | Out-Null

if (-not (Test-Path $rustupInit)) {
    Write-Host "Downloading rustup-init.exe into $downloadDir"
    Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupInit
}

$env:RUSTUP_HOME = $rustupHome
$env:CARGO_HOME = $cargoHome

& $rustupInit -y --no-modify-path --profile minimal --default-toolchain $Toolchain

$cargoBin = Join-Path $cargoHome "bin"
Write-Host ""
Write-Host "Rust toolchain installed locally."
Write-Host "For this PowerShell session, run:"
Write-Host "  `$env:RUSTUP_HOME='$rustupHome'"
Write-Host "  `$env:CARGO_HOME='$cargoHome'"
Write-Host "  `$env:Path='$cargoBin;' + `$env:Path"
