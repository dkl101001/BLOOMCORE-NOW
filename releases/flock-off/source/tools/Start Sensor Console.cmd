@echo off
setlocal
set "SENSOR_PYTHON=%~dp0..\.venv\Scripts\pythonw.exe"
if exist "%SENSOR_PYTHON%" (
  start "" "%SENSOR_PYTHON%" "%~dp0start_sensors.pyw"
  exit /b
)
set "SENSOR_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if exist "%SENSOR_PYTHON%" (
  start "" "%SENSOR_PYTHON%" "%~dp0start_sensors.pyw"
  exit /b
)
pyw -3 "%~dp0start_sensors.pyw"
