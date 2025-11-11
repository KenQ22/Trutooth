#!/usr/bin/env pwsh
# restart-backend.ps1
# Stops any running uvicorn processes and restarts the backend

Write-Host "Stopping any running TruTooth backend..." -ForegroundColor Yellow

# Try to stop uvicorn processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*trutooth*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

Write-Host "Starting TruTooth backend..." -ForegroundColor Green
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Start backend
uvicorn trutooth.api:app --reload
