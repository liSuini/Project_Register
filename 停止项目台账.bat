@echo off
title Project Ledger - Stop
echo ================================================
echo    Stop Project Ledger (backend 8100 / frontend 3000)
echo ================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" -Stop
echo.
echo Press any key to exit...
pause >nul
