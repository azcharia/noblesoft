$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Action
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"
$backendPython = Join-Path $backendPath "venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    throw "Backend virtualenv Python tidak ditemukan di: $backendPython"
}

Invoke-Step -Name "Backend compile check" -Action {
    Push-Location $backendPath
    try {
        & $backendPython -m compileall app
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Backend tests (pytest)" -Action {
    Push-Location $backendPath
    try {
        & $backendPython -m pytest
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Frontend lint" -Action {
    Push-Location $frontendPath
    try {
        npm run lint
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Frontend type-check" -Action {
    Push-Location $frontendPath
    try {
        npm run type-check
    }
    finally {
        Pop-Location
    }
}

Write-Host "`nPreflight selesai: semua check lulus." -ForegroundColor Green