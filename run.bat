@echo off
rem Bring the environment up to date, then start Sonic Rift without a console window.
setlocal
cd /d "%~dp0"

call setup_env.bat
if errorlevel 1 (
    echo.
    echo Setup failed. The newest logs\installer_*.log file explains why.
    pause
    exit /b 1
)

set "APP_PY=.venv\Scripts\pythonw.exe"
if not exist "%APP_PY%" set "APP_PY=.venv\Scripts\python.exe"
echo Launching main.py...
start "" "%APP_PY%" main.py
exit /b 0
