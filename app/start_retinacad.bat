@echo off
setlocal
set "APP_DIR=%~dp0"

where pythonw.exe >nul 2>nul
if %errorlevel%==0 (
  start "RetinaCAD" pythonw.exe "%APP_DIR%run_app.pyw"
  exit /b 0
)

where python.exe >nul 2>nul
if %errorlevel%==0 (
  python.exe "%APP_DIR%run_app.py"
  exit /b %errorlevel%
)

echo Python was not found. Install Python 3.11+ with Tk support.
pause
exit /b 1

