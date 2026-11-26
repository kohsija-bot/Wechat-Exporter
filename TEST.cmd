@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run RUN.cmd first to install dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -v
set RC=%ERRORLEVEL%
pause
exit /b %RC%
