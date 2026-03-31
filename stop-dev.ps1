$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $projectRoot ".runtime"
$pidFiles = @(
    (Join-Path $runtimeDir "backend.pid")
    (Join-Path $runtimeDir "frontend.pid")
)

$stoppedAny = $false

foreach ($pidFile in $pidFiles) {
    if (-not (Test-Path $pidFile)) {
        continue
    }

    $pidValue = Get-Content $pidFile -ErrorAction SilentlyContinue
    if (-not $pidValue) {
        Remove-Item $pidFile -ErrorAction SilentlyContinue
        continue
    }

    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($proc) {
        try {
            Stop-Process -Id $pidValue -Force
            Write-Host "Stopped PID $pidValue ($($proc.ProcessName))" -ForegroundColor Green
            $stoppedAny = $true
        }
        catch {
            Write-Host "Gagal stop PID ${pidValue}: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    Remove-Item $pidFile -ErrorAction SilentlyContinue
}

if (-not $stoppedAny) {
    Write-Host "Tidak ada process dev aktif dari pid file." -ForegroundColor Yellow
}

$fallbackTargets = Get-CimInstance Win32_Process |
    Where-Object {
        $cmd = $_.CommandLine
        if (-not $cmd) { return $false }

        $cmdLower = $cmd.ToLower()
        $rootLower = $projectRoot.ToLower()

        $isProjectProcess = $cmdLower.Contains($rootLower)
        $isBackendDev = $cmdLower.Contains("uvicorn app.main:app")
        $isFrontendDev = $cmdLower.Contains("next dev") -or $cmdLower.Contains("node_modules\\next\\dist\\bin\\next")

        return $isProjectProcess -and ($isBackendDev -or $isFrontendDev)
    }

foreach ($target in $fallbackTargets) {
    try {
        Stop-Process -Id $target.ProcessId -Force
        Write-Host "Stopped fallback PID $($target.ProcessId) ($($target.Name))" -ForegroundColor Green
        $stoppedAny = $true
    }
    catch {
        Write-Host "Gagal stop fallback PID $($target.ProcessId): $($_.Exception.Message)" -ForegroundColor Red
    }
}

try {
    $portPids = Get-NetTCPConnection -State Listen -LocalPort 3000, 8000 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($pidOnPort in $portPids) {
        $proc = Get-Process -Id $pidOnPort -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $pidOnPort -Force
            Write-Host "Stopped port listener PID $pidOnPort ($($proc.ProcessName))" -ForegroundColor Green
            $stoppedAny = $true
        }
    }
}
catch {
    Write-Host "Fallback port cleanup gagal: $($_.Exception.Message)" -ForegroundColor Red
}
