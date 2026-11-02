@echo off
rem Sonic Rift environment bootstrap for Windows.
rem Steps: check tools, make the Python 3.11 venv, refresh the lock, sync packages, install PyTorch.
rem Each step is skipped when its stamp file is newer than its inputs.
rem Set UV_APP_DRY=1 to skip the PyTorch step. Exit code 0 = ready, 1 = a step failed.
setlocal
cd /d "%~dp0"

set "WANT_PY=3.11"
set "VENV=.venv"
set "VENV_PY=%VENV%\Scripts\python.exe"
set "REQ_IN=requirements.in"
set "REQ_LOCK=requirements.lock.txt"
set "REQ_RUNTIME=%VENV%\.requirements.runtime.lock.txt"
set "STAMP_DEPS=%VENV%\.deps_installed"
set "STAMP_TORCH=%VENV%\.torch_checked"
set "TORCH_SCRIPT=scripts\install_torch.py"
if "%UV_APP_DRY%"=="" set "UV_APP_DRY=0"

rem One log per run; install_torch.py appends to the same file.
rem uv is run with "call" so a uv.cmd or uv.bat shim also returns here.
if not exist logs mkdir logs
for /f "usebackq" %%T in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"`) do set "RUN_ID=%%T"
set "LOG_FILE=logs\installer_%RUN_ID%.log"
set "CHATTERBOX_INSTALL_LOG=%CD%\%LOG_FILE%"

echo.
call :say "=== Starting Sonic Rift Installer ==="
echo Installer log: %LOG_FILE%
call :note "Dry Run Mode: %UV_APP_DRY%"

call :step_tools || goto failed
call :step_venv || goto failed
call :step_lock || goto failed
call :step_packages || goto failed
if not "%UV_APP_DRY%"=="0" goto dry_run
call :step_torch || goto failed
goto finished

:dry_run
call :say "[Dry Run] Skipped PyTorch installation"

:finished
call :say "Setup complete."
exit /b 0

:failed
call :note "Setup stopped after a failed step."
exit /b 1


rem ---- steps -----------------------------------------------------------------

:step_tools
where python >nul 2>nul
if errorlevel 1 (
    call :say "ERROR: Python was not found on PATH."
    echo Install Python %WANT_PY% from https://www.python.org/downloads/windows/
    echo and tick the installer's "Add python.exe to PATH" box, then run this again.
    exit /b 1
)
where uv >nul 2>nul
if errorlevel 1 (
    call :say "ERROR: uv was not found on PATH."
    echo Install it with "pip install uv" or see https://github.com/astral-sh/uv#getting-started/installation
    exit /b 1
)
call :note "python and uv are on PATH."
exit /b 0

:step_venv
if not exist "%VENV_PY%" goto venv_create
"%VENV_PY%" -c "import sys; sys.exit('.'.join(map(str, sys.version_info[:2])) != '%WANT_PY%')" >nul 2>nul
if not errorlevel 1 (
    call :note "%VENV% already runs Python %WANT_PY%."
    exit /b 0
)
call :say "%VENV% does not run Python %WANT_PY%; rebuilding it."
:venv_create
rem A new venv has no stamps, so every later step runs again.
if exist "%VENV%" rmdir /s /q "%VENV%"
call :say "Creating venv with Python %WANT_PY%..."
call uv venv "%VENV%" --python %WANT_PY% >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :say "ERROR: Could not create the virtual environment."
    exit /b 1
)
exit /b 0

:step_lock
call :is_stale "%REQ_LOCK%" "%REQ_IN%"
if "%STALE%"=="0" (
    call :say "Lock file already up to date."
    exit /b 0
)
call :say "Compiling %REQ_LOCK% from %REQ_IN%..."
call uv pip compile "%REQ_IN%" -o "%REQ_LOCK%" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :say "ERROR: Lock file generation failed."
    exit /b 1
)
exit /b 0

:step_packages
rem PyTorch comes from its own index in step_torch, so drop its pins here.
findstr /v /r /c:"^torch==" /c:"^torchaudio==" /c:"^torchvision==" "%REQ_LOCK%" >"%REQ_RUNTIME%"
if errorlevel 1 (
    call :say "ERROR: Could not write %REQ_RUNTIME%."
    exit /b 1
)
call :is_stale "%STAMP_DEPS%" "%REQ_LOCK%"
if "%STALE%"=="0" (
    call :say "Dependencies already installed. Skipping runtime dependency install."
    exit /b 0
)
call :say "Installing dependencies from lock file..."
call uv pip install --python "%VENV_PY%" -r "%REQ_RUNTIME%" --strict >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :say "ERROR: Dependency installation from lock file failed."
    exit /b 1
)
>"%STAMP_DEPS%" echo Dependencies synced from %REQ_RUNTIME%
exit /b 0

:step_torch
call :is_stale "%STAMP_TORCH%" "%TORCH_SCRIPT%" "%REQ_LOCK%"
"%VENV_PY%" -c "import torch, torchaudio, torchvision" >nul 2>nul
if errorlevel 1 (
    call :note "PyTorch does not import; reinstalling it."
    set "STALE=1"
)
if "%STALE%"=="0" (
    call :say "PyTorch already checked. Skipping install_torch.py."
    exit /b 0
)
if exist "%STAMP_TORCH%" del /q "%STAMP_TORCH%"
call :say "Installing PyTorch..."
"%VENV_PY%" "%TORCH_SCRIPT%"
if errorlevel 1 (
    call :say "WARNING: PyTorch install failed. App may lack GPU support."
    exit /b 1
)
>"%STAMP_TORCH%" echo PyTorch checked by install_torch.py
exit /b 0


rem ---- helpers ---------------------------------------------------------------

rem say TEXT: show it and log it.  note TEXT: log only.
:say
echo %~1
:note
>>"%LOG_FILE%" echo [%date% %time%] %~1
exit /b 0

rem is_stale TARGET SOURCE...: STALE=1 when TARGET is missing or older than any existing SOURCE.
:is_stale
set "STALE=1"
if not exist "%~1" exit /b 0
set "STALE=0"
set "STALE_TARGET=%~1"
:is_stale_next
shift
if "%~1"=="" exit /b 0
if exist "%~1" (
    powershell -NoProfile -Command "exit [int]((Get-Item -LiteralPath '%~1').LastWriteTimeUtc -gt (Get-Item -LiteralPath '%STALE_TARGET%').LastWriteTimeUtc)"
    if errorlevel 1 set "STALE=1"
)
goto is_stale_next
