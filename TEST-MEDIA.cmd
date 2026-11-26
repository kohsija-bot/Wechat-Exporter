@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run RUN.cmd first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m unittest -v test_media_catalog
pause
