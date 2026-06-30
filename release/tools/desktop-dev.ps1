$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "use-local-rust.ps1")

$desktopRoot = Resolve-Path (Join-Path $PSScriptRoot "..\desktop")
Push-Location $desktopRoot
try {
    npm run dev
} finally {
    Pop-Location
}
