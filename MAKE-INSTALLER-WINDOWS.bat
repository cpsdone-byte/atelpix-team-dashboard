@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Atelpix Windows Installer Builder

echo ================================================
echo   ATELPIX SECURE CLIENT DASHBOARD - BUILDER
echo ================================================
echo.
where py >nul 2>nul || (echo ERROR: Python 3.11 or newer is required. Install it from https://www.python.org/downloads/windows/ and enable Add Python to PATH.& pause & exit /b 1)
set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do if exist "%%~P" set "ISCC=%%~P"
if not defined ISCC (
  echo ERROR: Inno Setup 6 compiler was not found.
  echo Install Inno Setup 6 from https://jrsoftware.org/isinfo.php then run this file again.
  pause
  exit /b 1
)
call build_windows.bat
if errorlevel 1 exit /b 1
if not exist "dist\Atelpix Secure Dashboard.exe" (echo ERROR: App EXE was not created.& pause & exit /b 1)
"%ISCC%" installer.iss
if errorlevel 1 (echo ERROR: Installer compilation failed.& pause & exit /b 1)
if exist "installer-output\Atelpix-Secure-Client-Dashboard-Setup.exe" (
  echo.
  echo SUCCESS: installer-output\Atelpix-Secure-Client-Dashboard-Setup.exe
  echo Copy that installer to the Owner PC and both Team PCs.
) else (
  echo ERROR: Expected installer file was not found.
  pause
  exit /b 1
)
pause
