@echo off
title MBB Dalamud Bridge - Launcher
color 0A

echo ===============================================
echo    MBB Dalamud Bridge - Quick Launcher
echo ===============================================
echo.
echo Please select run mode:
echo.
echo [1] Debug Mode    - Show console output
echo [2] Hide IDE      - Run without console
echo [3] Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto debug
if "%choice%"=="2" goto hide
if "%choice%"=="3" goto exit
goto invalid

:debug
echo.
echo Starting MBB in Debug Mode...
python MBB.py
goto end

:hide
echo.
echo Starting MBB in Hide IDE Mode...
start /B pythonw MBB.py
echo MBB started successfully!
timeout /t 2
goto end

:invalid
echo.
echo Invalid choice! Please enter 1, 2, or 3
echo.
pause
cls
goto :eof

:exit
echo.
echo Goodbye!
timeout /t 2
goto end

:end
echo.
echo Press any key to close this window...
pause >nul