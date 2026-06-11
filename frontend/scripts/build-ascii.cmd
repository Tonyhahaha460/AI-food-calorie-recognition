@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "FRONTEND_DIR=%%~fI"
set "VIRTUAL_DRIVE=X:"

subst %VIRTUAL_DRIVE% /d >nul 2>&1
subst %VIRTUAL_DRIVE% "%FRONTEND_DIR%"
if errorlevel 1 (
  echo Failed to create temporary ASCII drive mapping for "%FRONTEND_DIR%".
  exit /b 1
)

pushd %VIRTUAL_DRIVE%\
call node_modules\.bin\vite.cmd build
set "EXITCODE=%ERRORLEVEL%"
popd

subst %VIRTUAL_DRIVE% /d >nul 2>&1
exit /b %EXITCODE%
