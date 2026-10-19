@echo off
setlocal
title J.A.R.V.I.S. MARK LVI -- HOLOGRAPHIC NEURAL CORE
cd /d "%~dp0"

echo =====================================================================
echo  J.A.R.V.I.S. MARK LVI -- 3D HOLOGRAPHIC NEURAL CORE LAUNCHER
echo =====================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo [Launcher] Using dedicated virtual environment: .venv
    ".venv\Scripts\python.exe" main.py %*
) else (
    echo [Launcher] .venv not found. Using system python
    python main.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Launcher] Process terminated with error code %ERRORLEVEL%.
    pause
)
