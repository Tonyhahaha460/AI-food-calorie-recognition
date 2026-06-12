@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

for %%I in ("%~dp0.") do set "ROOT_DIR=%%~fI"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "BACKEND_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "BACKEND_REQUIREMENTS=%BACKEND_DIR%\requirements.txt"
set "WORK_TMP=%ROOT_DIR%\tmp"
set "PYTHON_BOOTSTRAP_CMD="
set "PYTHON_BOOTSTRAP_ARGS="
set "NPM_CMD="

echo.
echo ========================================
echo AI Food Calorie Recognition - Install
echo ========================================
echo.

if not exist "%BACKEND_DIR%" (
  echo [ERROR] backend folder not found.
  echo Please run this file from the project root folder.
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%" (
  echo [ERROR] frontend folder not found.
  echo Please run this file from the project root folder.
  pause
  exit /b 1
)

if not exist "%WORK_TMP%" (
  mkdir "%WORK_TMP%" >nul 2>nul
)

set "TEMP=%WORK_TMP%"
set "TMP=%WORK_TMP%"

echo [1/6] Checking Node.js and npm...
where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found.
  echo Please install Node.js LTS first:
  echo https://nodejs.org/
  echo.
  echo After installing Node.js, close this window and run this file again.
  pause
  exit /b 1
)
set "NPM_CMD=npm.cmd"
call "%NPM_CMD%" --version

echo.
echo [2/6] Checking Python...
where py.exe >nul 2>nul
if not errorlevel 1 (
  py -3.13 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_BOOTSTRAP_CMD=py.exe"
    set "PYTHON_BOOTSTRAP_ARGS=-3.13"
  )
)

if not defined PYTHON_BOOTSTRAP_CMD (
  where py.exe >nul 2>nul
  if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP_CMD=py.exe"
      set "PYTHON_BOOTSTRAP_ARGS=-3.12"
    )
  )
)

if not defined PYTHON_BOOTSTRAP_CMD (
  where py.exe >nul 2>nul
  if not errorlevel 1 (
    py -3.11 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP_CMD=py.exe"
      set "PYTHON_BOOTSTRAP_ARGS=-3.11"
    )
  )
)

if not defined PYTHON_BOOTSTRAP_CMD (
  where py.exe >nul 2>nul
  if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP_CMD=py.exe"
      set "PYTHON_BOOTSTRAP_ARGS=-3"
    )
  )
)

if not defined PYTHON_BOOTSTRAP_CMD (
  where python.exe >nul 2>nul
  if not errorlevel 1 (
    python.exe -c "import sys" >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_BOOTSTRAP_CMD=python.exe"
      set "PYTHON_BOOTSTRAP_ARGS="
    )
  )
)

if not defined PYTHON_BOOTSTRAP_CMD (
  echo [ERROR] Python not found.
  echo Please install Python 3.11, 3.12, or 3.13 first:
  echo https://www.python.org/downloads/
  echo.
  echo Important: enable "Add python.exe to PATH" during installation.
  pause
  exit /b 1
)

call "%PYTHON_BOOTSTRAP_CMD%" %PYTHON_BOOTSTRAP_ARGS% --version

echo.
echo [3/6] Creating environment files if needed...
if not exist "%BACKEND_DIR%\.env" (
  if exist "%BACKEND_DIR%\.env.example" (
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    echo Created backend\.env from backend\.env.example
  ) else (
    echo [WARN] backend\.env.example not found. Skipping backend .env creation.
  )
) else (
  echo backend\.env already exists. Keeping current file.
)

if not exist "%FRONTEND_DIR%\.env" (
  if exist "%FRONTEND_DIR%\.env.example" (
    copy "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul
    echo Created frontend\.env from frontend\.env.example
  ) else (
    echo [WARN] frontend\.env.example not found. Skipping frontend .env creation.
  )
) else (
  echo frontend\.env already exists. Keeping current file.
)

echo.
echo [4/6] Preparing backend Python virtual environment...
if not exist "%BACKEND_PYTHON%" (
  pushd "%BACKEND_DIR%"
  call "%PYTHON_BOOTSTRAP_CMD%" %PYTHON_BOOTSTRAP_ARGS% -m venv .venv
  set "CREATE_VENV_EXIT=%ERRORLEVEL%"
  popd
  if not "!CREATE_VENV_EXIT!"=="0" (
    echo [ERROR] Failed to create backend virtual environment.
    pause
    exit /b 1
  )
) else (
  echo backend\.venv already exists. Reusing current environment.
)

"%BACKEND_PYTHON%" -m pip --version >nul 2>nul
if errorlevel 1 (
  echo Bootstrapping pip...
  "%BACKEND_PYTHON%" -m ensurepip --default-pip
  if errorlevel 1 (
    echo [ERROR] Failed to install pip inside backend\.venv.
    pause
    exit /b 1
  )
)

echo Installing backend Python packages...
"%BACKEND_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  pause
  exit /b 1
)

if exist "%BACKEND_REQUIREMENTS%" (
  "%BACKEND_PYTHON%" -m pip install -r "%BACKEND_REQUIREMENTS%"
  if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install backend requirements.
    echo Check your internet connection and Python version, then run this file again.
    pause
    exit /b 1
  )
) else (
  echo [ERROR] backend\requirements.txt not found.
  pause
  exit /b 1
)

echo.
echo [5/6] Installing frontend packages...
pushd "%FRONTEND_DIR%"
if exist "package-lock.json" (
  call "%NPM_CMD%" ci
) else (
  call "%NPM_CMD%" install
)
set "NPM_INSTALL_EXIT=%ERRORLEVEL%"
popd
if not "!NPM_INSTALL_EXIT!"=="0" (
  echo [ERROR] Failed to install frontend packages.
  pause
  exit /b 1
)

echo.
echo [6/6] Verifying project startup files...
if not exist "%BACKEND_DIR%\run.py" (
  echo [ERROR] backend\run.py not found.
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] frontend\package.json not found.
  pause
  exit /b 1
)

echo.
echo ========================================
echo Installation complete.
echo ========================================
echo.
echo Next step:
echo   Run 啟動前後端.bat
echo.
echo Local URLs after startup:
echo   Backend:  http://localhost:5000
echo   Frontend: http://localhost:5173
echo.
pause
