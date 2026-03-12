@echo off
REM Usage: run_server.bat [port]

set "PORT=5000"
if not "%~1"=="" set "PORT=%~1"

REM Try to activate a virtualenv in the repo root or indicator_prototype
if exist "%~dp0\.venv\Scripts\activate.bat" (
  call "%~dp0\.venv\Scripts\activate.bat"
) else if exist "%~dp0\indicator_prototype\.venv\Scripts\activate.bat" (
  call "%~dp0\indicator_prototype\.venv\Scripts\activate.bat"
)

echo Starting Flask server (app.py) on port %PORT%...
set PORT=%PORT%
pushd "%~dp0"
python app.py
popd
