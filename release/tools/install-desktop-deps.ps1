$ErrorActionPreference = "Stop"

$desktopRoot = Resolve-Path (Join-Path $PSScriptRoot "..\desktop")
Push-Location $desktopRoot
try {
    npm install
} finally {
    Pop-Location
}
