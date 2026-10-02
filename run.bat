@echo off
cd /d "%~dp0"
if exist venv\Scripts\python.exe (
    .\venv\Scripts\python.exe main.py
) else (
    echo Virtual environment not found. Running setup.bat first...
    call setup.bat
    .\venv\Scripts\python.exe main.py
)
pause
