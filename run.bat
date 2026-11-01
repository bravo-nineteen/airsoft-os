@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Python is required. Install Python 3.12 or later from python.org.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 py -m venv .venv
 if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" main.py
exit /b %errorlevel%
:fail
echo AOJ OS setup failed. Check the errors above.
pause
exit /b 1
