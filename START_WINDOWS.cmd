@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ is required for this SOURCE launcher.
    echo Install Python from python.org or use the Windows EXE produced by GitHub Actions.
    pause
    exit /b 1
  )
  py -3 -m venv ".venv"
  if errorlevel 1 (echo Could not create Python virtual environment.& pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (echo Could not install dependencies. Internet may be needed on first setup.& pause & exit /b 1)
".venv\Scripts\python.exe" -m vericorpus.desktop
if errorlevel 1 pause
endlocal
