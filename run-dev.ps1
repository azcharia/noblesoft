$ErrorActionPreference = "Stop"

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $end = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $end) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"
$backendPython = Join-Path $backendPath "venv\Scripts\python.exe"
$runtimeDir = Join-Path $projectRoot ".runtime"

if (-not (Test-Path $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

$backendPidFile = Join-Path $runtimeDir "backend.pid"
$frontendPidFile = Join-Path $runtimeDir "frontend.pid"
$backendLog = Join-Path $runtimeDir "backend-dev.out.log"
$backendErrLog = Join-Path $runtimeDir "backend-dev.err.log"
$frontendLog = Join-Path $runtimeDir "frontend-dev.out.log"
$frontendErrLog = Join-Path $runtimeDir "frontend-dev.err.log"

if (-not (Test-Path $backendPython)) {
    throw "Backend virtualenv Python tidak ditemukan di: $backendPython"
}

if (-not (Test-Path (Join-Path $frontendPath "node_modules"))) {
    Write-Host "node_modules frontend belum ada. Menjalankan npm install..." -ForegroundColor Yellow
    Push-Location $frontendPath
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

if (Test-Path $backendPidFile) {
    $existingBackendPid = Get-Content $backendPidFile -ErrorAction SilentlyContinue
    if ($existingBackendPid -and (Get-Process -Id $existingBackendPid -ErrorAction SilentlyContinue)) {
        Write-Host "Backend sudah berjalan (PID: $existingBackendPid)." -ForegroundColor Yellow
    }
    else {
        Remove-Item $backendPidFile -ErrorAction SilentlyContinue
    }
}

if (Test-Path $frontendPidFile) {
    $existingFrontendPid = Get-Content $frontendPidFile -ErrorAction SilentlyContinue
    if ($existingFrontendPid -and (Get-Process -Id $existingFrontendPid -ErrorAction SilentlyContinue)) {
        Write-Host "Frontend sudah berjalan (PID: $existingFrontendPid)." -ForegroundColor Yellow
    }
    else {
        Remove-Item $frontendPidFile -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $backendPidFile)) {
    $backendProcess = Start-Process -FilePath $backendPython `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
        -WorkingDirectory $backendPath `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendErrLog `
        -PassThru

    $backendProcess.Id | Set-Content $backendPidFile
    Write-Host "Backend started (PID: $($backendProcess.Id)) at http://localhost:8000" -ForegroundColor Green
}

if (-not (Test-Path $frontendPidFile)) {
    $frontendProcess = Start-Process -FilePath "node.exe" `
        -ArgumentList ".\\node_modules\\next\\dist\\bin\\next", "dev" `
        -WorkingDirectory $frontendPath `
        -RedirectStandardOutput $frontendLog `
        -RedirectStandardError $frontendErrLog `
        -PassThru

    $frontendProcess.Id | Set-Content $frontendPidFile
    Write-Host "Frontend started (PID: $($frontendProcess.Id)) at http://localhost:3000" -ForegroundColor Green
}

$backendReady = Wait-HttpReady -Url "http://localhost:8000/health" -TimeoutSeconds 30
$frontendReady = Wait-HttpReady -Url "http://localhost:3000" -TimeoutSeconds 45

if (-not $backendReady) {
    Write-Host "Backend belum merespons. Cek log: $backendLog" -ForegroundColor Red
}

if (-not $frontendReady) {
    Write-Host "Frontend belum merespons. Cek log: $frontendLog" -ForegroundColor Red
}

if ($backendReady -and $frontendReady) {
    Write-Host "Fullstack dev environment siap." -ForegroundColor Green
}

Write-Host "Gunakan .\stop-dev.ps1 untuk menghentikan process dev." -ForegroundColor Cyan
