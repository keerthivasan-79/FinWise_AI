@echo off
setlocal
set "ROOT=%~dp0"

cd /d "%ROOT%frontend"
echo Building FinWise interface...
call npm run build
if errorlevel 1 exit /b %errorlevel%

cd /d "%ROOT%backend"
echo Starting FinWise at http://127.0.0.1:5000
set "PYTHON_CMD="

if defined VIRTUAL_ENV (
  if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
    "%VIRTUAL_ENV%\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD="%VIRTUAL_ENV%\Scripts\python.exe""
  )
)

if not defined PYTHON_CMD (
  if exist "%ROOT%.venv\Scripts\python.exe" (
    "%ROOT%.venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD="%ROOT%.venv\Scripts\python.exe""
  )
)

if not defined PYTHON_CMD (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  echo.
  echo FinWise could not find a working Python.
  echo Try reinstalling Python or recreating the virtual environment.
  echo.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import importlib; mods=['flask','flask_cors','mysql.connector','jwt','werkzeug','openpyxl','reportlab','xlrd','pdfplumber']; [importlib.import_module(m) for m in mods]; print('Python dependencies OK')"
if errorlevel 1 (
  echo.
  echo FinWise could not import one or more Python packages.
  echo The error above shows the exact package.
  echo Run: %PYTHON_CMD% -m pip install -r "%ROOT%backend\requirements.txt"
  echo.
  pause
  exit /b 1
)

%PYTHON_CMD% app.py
