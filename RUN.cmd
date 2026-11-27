@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
py -3.14 -c "import struct; assert struct.calcsize('P')==8" || goto fail
if not exist ".venv\Scripts\python.exe" (
  py -3.14 -m venv .venv || goto fail
)
".venv\Scripts\python.exe" -c "import PySide6,psutil,Cryptodome,zstandard,xlsxwriter,PIL,imageio_ffmpeg" >nul 2>&1
if errorlevel 1 (
  echo Installing required packages from PyPI. Internet is required once.
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto fail
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo.
echo Startup failed. Copy the error above. Requires Windows x64 and Python 3.14 x64.
pause
exit /b 1
