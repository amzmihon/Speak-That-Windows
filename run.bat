@echo off
title SpeakThat Windows Text Reader
cd /d "%~dp0"

echo ===================================================
echo           SpeakThat - Windows Text Reader          
echo       Powered by Paradee 8M ONNX Speech Engine     
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" goto use_venv
goto use_system

:use_venv
echo [*] Starting SpeakThat using virtual environment...
".venv\Scripts\python.exe" -u main.py
goto finish

:use_system
echo [*] Starting SpeakThat using system Python...
python -u main.py
goto finish

:finish
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Application exited with error code %ERRORLEVEL%.
    pause
)
