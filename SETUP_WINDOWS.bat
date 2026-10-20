@echo off
setlocal
cd /d "%~dp0"
echo U^&I Dispatch AI - Install local demo
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo Setup complete. Run START_WINDOWS.bat then open http://127.0.0.1:8000
pause
exit /b 0
:fail
echo.
echo Setup failed. Check Python 3.11+, Internet, and README.md.
pause
exit /b 1
