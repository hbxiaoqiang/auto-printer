#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Building Auto Printer for Windows..." -ForegroundColor Cyan

# 检查 Python
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    Write-Error "Python not found. Please install Python 3.11+ first."
    exit 1
}

# 创建虚拟环境
if (-not (Test-Path "$ProjectRoot\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Green
    & python -m venv "$ProjectRoot\.venv"
}

& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install -r "$ProjectRoot\requirements.txt"
& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install pyinstaller

# 清理旧构建
Remove-Item -Path "$ProjectRoot\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$ProjectRoot\dist" -Recurse -Force -ErrorAction SilentlyContinue

# 打包
& "$ProjectRoot\.venv\Scripts\pyinstaller.exe" "$ProjectRoot\auto-printer.spec" --clean --noconfirm

if (Test-Path "$ProjectRoot\dist\auto-printer.exe") {
    Write-Host "Build successful: $ProjectRoot\dist\auto-printer.exe" -ForegroundColor Green
} else {
    Write-Error "Build failed: auto-printer.exe not found."
    exit 1
}
