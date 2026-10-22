@echo off
title Project Ledger - Start
echo ================================================
echo    Project Ledger - One Project One Account
echo ================================================
echo.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Start failed. Press any key to exit...
  pause >nul
  exit /b 1
)
echo.
echo Browser will open http://localhost:3000 - this window closes in 5s.
ping -n 6 127.0.0.1 >nul
