@echo off
rem Start menu entry point for an installed copy of Sonic Rift.
rem The installer ships uv in tools\, and uv provides Python 3.11, so users
rem don't need to install either tool themselves. run.bat does the rest.
setlocal
cd /d "%~dp0"
set "PATH=%~dp0tools;%PATH%"

uv python find 3.11 >nul 2>nul
if errorlevel 1 (
    echo Installing a private copy of Python 3.11 for Sonic Rift...
    uv python install 3.11
    if errorlevel 1 goto :fail
)
for /f "delims=" %%p in ('uv python find 3.11') do set "PATH=%%~dpp;%PATH%"

call "%~dp0run.bat"
exit /b %ERRORLEVEL%

:fail
echo.
echo Could not install Python 3.11. Check your internet connection and try again.
pause
exit /b 1
