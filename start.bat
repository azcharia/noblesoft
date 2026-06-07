@echo off
echo Menghentikan proses yang sedang berjalan...
powershell -ExecutionPolicy Bypass -File ".\stop-dev.ps1"

echo Memulai ulang NobleSoft Fullstack (Backend & Frontend)...
powershell -ExecutionPolicy Bypass -File ".\run-dev.ps1"

echo.
echo ====================================================
echo NobleSoft siap diakses di:
echo [Frontend] http://localhost:3000
echo [Backend ] http://localhost:8000
echo ====================================================
echo.
pause
