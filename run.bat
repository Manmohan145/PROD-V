@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Starting VisionAI Full-Stack Application...
echo ==========================================

:: Change directory to the script's directory to ensure relative paths work
cd /d "%~dp0"

:: Check if virtual environment directory exists
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment 'venv' not found. Creating virtual environment...
    python -m venv venv
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
