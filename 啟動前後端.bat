@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

for %%I in ("%~dp0.") do set "ROOT_DIR=%%~fI"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "BACKEND_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_REQUIREMENTS=%BACKEND_DIR%\requirements.txt"
set "WORK_TMP=%ROOT_DIR%\tmp"
set "PYTHON_BOOTSTRAP="
set "NPM_CMD="

if not exist "%BACKEND_DIR%" (
  echo [ERROR] backend folder not found.
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%" (
  echo [ERROR] frontend folder not found.
  pause
  exit /b 1
)

if not exist "%WORK_TMP%" (
  mkdir "%WORK_TMP%" >nul 2>nul
)

set "TEMP=%WORK_TMP%"
set "TMP=%WORK_TMP%"

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found. Please install Node.js first.
  pause
  exit /b 1
)
set "NPM_CMD=npm.cmd"

where py.exe >nul 2>nul
if not errorlevel 1 (
  py -3.13 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_BOOTSTRAP=py -3.13"
  )
)

if not defined PYTHON_BOOTSTRAP (
  where py.exe >nul 2>nul
  if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP=py -3"
    )
  )
)

if not defined PYTHON_BOOTSTRAP (
  where python.exe >nul 2>nul
  if not errorlevel 1 (
    python.exe -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP=python.exe"
    )
  )
)

if not defined PYTHON_BOOTSTRAP (
  if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    )
  )
)

if not defined PYTHON_BOOTSTRAP (
  if exist "%ProgramFiles%\Python313\python.exe" (
    "%ProgramFiles%\Python313\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP=%ProgramFiles%\Python313\python.exe"
    )
  )
)

if exist "%BACKEND_PYTHON%" (
  "%BACKEND_PYTHON%" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo [WARN] Existing backend virtual environment is broken.
    if defined PYTHON_BOOTSTRAP (
      echo [INFO] Recreating backend virtual environment...
      rmdir /s /q "%BACKEND_DIR%\.venv"
    ) else (
      echo [ERROR] Python not found, and the existing backend virtual environment cannot run.
      echo [ERROR] Please install Python 3.13, then run this file again.
      pause
      exit /b 1
    )
  )
)

if not exist "%BACKEND_PYTHON%" (
  if not defined PYTHON_BOOTSTRAP (
    echo [ERROR] Python not found. Please install Python 3.13 first.
    pause
    exit /b 1
  )
  echo [INFO] Creating backend virtual environment...
  pushd "%BACKEND_DIR%"
  call %PYTHON_BOOTSTRAP% -m venv .venv
  set "CREATE_VENV_EXIT=%ERRORLEVEL%"
  popd
  if not "!CREATE_VENV_EXIT!"=="0" (
    echo [ERROR] Failed to create backend virtual environment.
    pause
    exit /b 1
  )
)

if not exist "%BACKEND_PYTHON%" (
  echo [ERROR] backend Python not found:
  echo %BACKEND_PYTHON%
  pause
  exit /b 1
)

echo [INFO] Checking backend pip...
"%BACKEND_PYTHON%" -m pip --version >nul 2>nul
if errorlevel 1 (
  echo [INFO] Bootstrapping pip inside backend virtual environment...
  "%BACKEND_PYTHON%" -m ensurepip --default-pip
  if errorlevel 1 (
    echo [ERROR] Failed to bootstrap pip in backend virtual environment.
    pause
    exit /b 1
  )
)

if exist "%BACKEND_REQUIREMENTS%" (
  pushd "%BACKEND_DIR%"
  "%BACKEND_PYTHON%" -c "from app import create_app; create_app()" >nul 2>nul
  set "BACKEND_READY_EXIT=%ERRORLEVEL%"
  popd
  if not "!BACKEND_READY_EXIT!"=="0" (
    echo [INFO] Installing backend requirements...
    "%BACKEND_PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 (
      echo [ERROR] Failed to upgrade pip.
      pause
      exit /b 1
    )
    "%BACKEND_PYTHON%" -m pip install -r "%BACKEND_REQUIREMENTS%"
    if errorlevel 1 (
      echo [ERROR] Failed to install backend requirements.
      pause
      exit /b 1
    )
  )

  pushd "%BACKEND_DIR%"
  "%BACKEND_PYTHON%" -c "from app import create_app; create_app()" >nul 2>nul
  set "BACKEND_READY_EXIT=%ERRORLEVEL%"
  popd
  if not "!BACKEND_READY_EXIT!"=="0" (
    echo [ERROR] Backend environment is still not ready after dependency install.
    echo [ERROR] Details:
    pushd "%BACKEND_DIR%"
    "%BACKEND_PYTHON%" -c "from app import create_app; create_app()"
    popd
    pause
    exit /b 1
  )
)

if not exist "%FRONTEND_DIR%\node_modules" (
  echo [INFO] Installing frontend dependencies...
  pushd "%FRONTEND_DIR%"
  call "%NPM_CMD%" install
  set "NPM_INSTALL_EXIT=%ERRORLEVEL%"
  popd
  if not "!NPM_INSTALL_EXIT!"=="0" (
    echo [ERROR] Failed to install frontend dependencies.
    pause
    exit /b 1
  )
)

echo Starting backend...
start "AI Food Journal Backend" /D "%BACKEND_DIR%" cmd /k ""%BACKEND_PYTHON%" "run.py""

echo Starting frontend...
start "AI Food Journal Frontend" /D "%FRONTEND_DIR%" cmd /k "%NPM_CMD% run dev"

echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Two new windows should open for backend and frontend.
pause
