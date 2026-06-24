@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Starting VisionAI Full-Stack Application...
echo ==========================================

:: Change directory to the script's directory to ensure relative paths work
cd /d "%~dp0"

:: Check if virtual environment exists AND its Python actually runs on this machine.
:: A venv folder copied in from another PC/user account has hardcoded interpreter
:: paths and will silently fail to launch, so detect that and rebuild it.
set "NEED_VENV=0"
if not exist "venv\Scripts\python.exe" (
    set "NEED_VENV=1"
) else (
    venv\Scripts\python.exe -c "" >nul 2>&1
    if !errorlevel! neq 0 set "NEED_VENV=1"
)

if "!NEED_VENV!"=="1" (
    if exist "venv" (
        echo [INFO] Existing 'venv' is broken or from another machine. Rebuilding it...
        rmdir /s /q venv
    ) else (
        echo [INFO] Virtual environment 'venv' not found. Creating virtual environment...
    )

    where py >nul 2>&1
    if !errorlevel! equ 0 (
        py -3 -m venv venv
    ) else (
        python -m venv venv
    )
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment. Please check if Python is installed and added to PATH.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Checking/installing Python dependencies...
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [WARNING] Dependency installation finished with issues. Trying to start anyway...
)

:: Check if npm packages are installed
if not exist "node_modules" (
    echo [INFO] node_modules not found. Installing SvelteKit node dependencies...
    cmd.exe /c npm install
)

echo.
echo Stopping any previous backend on port 8000...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)

echo Launching FastAPI backend server on http://localhost:8000...
start "VisionAI-API" /b venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo Launching SvelteKit frontend server on http://localhost:5173...
start "VisionAI-Frontend" /b cmd.exe /c npm run dev

echo Waiting for servers to initialize...
timeout /t 5 /nobreak >nul

echo Opening browser at http://localhost:5173...
start http://localhost:5173

echo.
echo Application running!
echo Close this command prompt window to stop the servers.
echo ==========================================

:: Keep script alive so the background start /b tasks remain attached to the console
pause >nul
