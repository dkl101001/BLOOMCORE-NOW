@echo off
setlocal
set "DESK_PYTHON=%~dp0..\.venv\Scripts\pythonw.exe"
if exist "%DESK_PYTHON%" (
  start "" "%DESK_PYTHON%" "%~dp0start_desk.pyw"
  exit /b
)
set "DESK_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if exist "%DESK_PYTHON%" (
  start "" "%DESK_PYTHON%" "%~dp0start_desk.pyw"
  exit /b
)
pyw -3 "%~dp0start_desk.pyw"
if errorlevel 1 (
  echo Install Python 3.12 or newer with Tk and the requirements.lock dependencies first.
  pause
)
