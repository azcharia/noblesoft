$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"
$backendPython = Join-Path $backendPath "venv\Scripts\python.exe"

# Stop existing processes first to free the ports
Write-Host "Stopping existing servers..." -ForegroundColor Cyan
try {
    # Try using stop-dev.ps1 if it exists
    $stopScript = Join-Path $projectRoot "stop-dev.ps1"
    if (Test-Path $stopScript) {
        & $stopScript | Out-Null
    }
} catch {}

Write-Host "Starting Backend Job..." -ForegroundColor Green
$backendJob = Start-Job -Name "NobleSoft-Backend" -ScriptBlock {
    param($py, $path)
    Set-Location $path
    & $py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $backendPython, $backendPath

Write-Host "Starting Frontend Job..." -ForegroundColor Green
$frontendJob = Start-Job -Name "NobleSoft-Frontend" -ScriptBlock {
    param($path)
    Set-Location $path
    npm run dev
} -ArgumentList $frontendPath

Write-Host "Both servers are running in PowerShell Jobs!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Keeping this task alive to prevent sandbox cleanup. Do not terminate." -ForegroundColor Yellow

# Infinite loop to keep the parent process running and the jobs alive
try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
}
finally {
    Write-Host "Stopping jobs..." -ForegroundColor Red
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
    Remove-Job $frontendJob -Force -ErrorAction SilentlyContinue
}
