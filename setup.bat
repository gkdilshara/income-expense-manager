@echo off
echo ============================================================
echo   Income ^& Expenses Manager CLI - Setup
echo   Created by Sasindu Dilshara
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

:: Create virtual environment
echo [1/4] Creating virtual environment...
if not exist venv (
    python -m venv venv
)
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

:: Upgrade pip inside venv
echo [2/4] Upgrading pip...
.\venv\Scripts\python.exe -m pip install --upgrade pip --quiet

:: Install dependencies
echo [3/4] Installing dependencies...
.\venv\Scripts\pip.exe install -r requirements.txt

:: Copy .env if not exists
echo [4/4] Setting up environment configuration...
if not exist .env (
    copy .env.example .env
    echo [INFO] Created .env from template. Edit it to configure MySQL if needed.
)

:: Create directories
if not exist data mkdir data
if not exist exports mkdir exports
if not exist backups mkdir backups

echo.
echo ============================================================
echo   Setup complete!
echo   Run the app with:  run.bat
echo   Or run directly:   .\venv\Scripts\python.exe main.py
echo ============================================================
echo.
pause
