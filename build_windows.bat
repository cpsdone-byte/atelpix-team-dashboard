@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3.11+ is required only to BUILD the installer. & pause & exit /b 1)
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name "Atelpix Secure Dashboard" --collect-all cryptography --hidden-import zoneinfo main.py
if errorlevel 1 goto fail
echo Build completed: dist\Atelpix Secure Dashboard.exe
 echo Next compile installer.iss using Inno Setup 6 (builder only).
pause
exit /b 0
:fail
echo Build failed. Review the error above.
pause
exit /b 1
