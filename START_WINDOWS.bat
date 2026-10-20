@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
echo Website: http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo Keep this window open. Press Ctrl+C to stop.
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 pause
