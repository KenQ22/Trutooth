#!/usr/bin/env pwsh
# start-trutooth.ps1
# Launches the TruTooth backend API and GUI control center in separate windows.

$ErrorActionPreference = "Stop"

# Determine project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "TruTooth Project Root: $ProjectRoot" -ForegroundColor Cyan

# Check for Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check for Java
if (Get-Command java -ErrorAction SilentlyContinue) {
    Write-Host "Found Java" -ForegroundColor Green
} else {
    Write-Host "ERROR: Java is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check for Maven
if (Get-Command mvn -ErrorAction SilentlyContinue) {
    Write-Host "Found Maven" -ForegroundColor Green
} else {
    Write-Host "ERROR: Maven is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting TruTooth Backend API..." -ForegroundColor Yellow

# Start backend in a new PowerShell window
$backendScript = @"
Set-Location '$ProjectRoot'
if (Test-Path "$ProjectRoot\venv\Scripts\activate.ps1") {
    Write-Host 'Activating venv (venv)...' -ForegroundColor Cyan
    . "$ProjectRoot\venv\Scripts\activate.ps1"
} elseif (Test-Path "$ProjectRoot\.venv\Scripts\activate.ps1") {
    Write-Host 'Activating venv (.venv)...' -ForegroundColor Cyan
    . "$ProjectRoot\.venv\Scripts\activate.ps1"
} else {
    Write-Host 'No virtual environment found; using system Python.' -ForegroundColor Yellow
}
Write-Host 'Starting FastAPI backend on http://127.0.0.1:8000...' -ForegroundColor Cyan
uvicorn trutooth.api:app --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

# Give backend a moment to initialize
Write-Host "Waiting 3 seconds for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting TruTooth GUI..." -ForegroundColor Yellow

# Start GUI in a new PowerShell window
$guiScript = @"
Set-Location '$ProjectRoot\java'
Write-Host 'Launching TruTooth Control Center...' -ForegroundColor Cyan
mvn -q exec:java
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $guiScript

Write-Host ""
Write-Host "TruTooth is now running!" -ForegroundColor Green
Write-Host "Backend API: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "GUI Control Center: Launching in separate window" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the backend and GUI windows when finished." -ForegroundColor Yellow
