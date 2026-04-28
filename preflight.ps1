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
        if ($LASTEXITCODE -ne 0) {
            throw "Backend compile check failed"
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Backend schema probe (Phase 5 operations)" -Action {
    Push-Location $backendPath
    try {
        & $backendPython scripts\check_phase5_schema.py
        $schemaProbeExitCode = $LASTEXITCODE

        if ($schemaProbeExitCode -eq 1) {
            throw "Schema probe failed. Apply Phase 5 migration and rerun preflight."
        }

        if ($schemaProbeExitCode -eq 2) {
            Write-Host "Schema probe skipped (missing or placeholder Supabase credentials)." -ForegroundColor Yellow
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Backend tests (pytest)" -Action {
    Push-Location $backendPath
    try {
        & $backendPython -m pytest
        if ($LASTEXITCODE -ne 0) {
            throw "Backend tests failed"
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Frontend lint" -Action {
    Push-Location $frontendPath
    try {
        npm run lint
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend lint failed"
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "Frontend type-check" -Action {
    Push-Location $frontendPath
    try {
        npm run type-check
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend type-check failed"
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "`nPreflight selesai: semua check lulus." -ForegroundColor Green