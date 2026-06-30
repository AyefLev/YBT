$ErrorActionPreference = "Stop"

$releaseRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$targets = @(
    (Join-Path $releaseRoot ".toolchains"),
    (Join-Path $releaseRoot "desktop\node_modules"),
    (Join-Path $releaseRoot "desktop\src-tauri\target")
)

foreach ($target in $targets) {
    if (-not (Test-Path $target)) {
        continue
    }

    $resolved = (Resolve-Path $target).Path
    if (-not $resolved.StartsWith($releaseRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside release root: $resolved"
    }

    Write-Host "Removing $resolved"
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

Write-Host "Local release tooling cleaned."
