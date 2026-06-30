$ErrorActionPreference = "Stop"

$iconDir = Resolve-Path (Join-Path $PSScriptRoot "..\desktop\src-tauri")
$iconDir = Join-Path $iconDir "icons"
New-Item -ItemType Directory -Force -Path $iconDir | Out-Null

Add-Type -AssemblyName System.Drawing

$bitmap = [System.Drawing.Bitmap]::new(256, 256)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::FromArgb(37, 99, 235))

$font = [System.Drawing.Font]::new("Microsoft YaHei UI", 104, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
$format = [System.Drawing.StringFormat]::new()
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Center
$rect = [System.Drawing.RectangleF]::new(0, 0, 256, 246)
$graphics.DrawString("Y", $font, $brush, $rect, $format)

$pngPath = Join-Path $iconDir "icon.png"
$icoPath = Join-Path $iconDir "icon.ico"
$bitmap.Save($pngPath, [System.Drawing.Imaging.ImageFormat]::Png)

$iconHandle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($iconHandle)
$stream = [System.IO.File]::Open($icoPath, [System.IO.FileMode]::Create)
try {
    $icon.Save($stream)
} finally {
    $stream.Dispose()
    $icon.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}

Write-Host "Generated $icoPath"
