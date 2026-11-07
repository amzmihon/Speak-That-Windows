@echo off
title SpeakThat Windows Text Reader
cd /d "%~dp0"

echo ===================================================
echo           SpeakThat - Windows Text Reader          
echo       Powered by Paradee 8M ONNX Speech Engine     
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo [*] Starting SpeakThat using virtual environment...
    ".venv\Scripts\python.exe" -u main.py
    set "APP_EXIT_CODE=%ERRORLEVEL%"
    goto finish
)

echo [!] Virtual environment (.venv) not found. Trying system Python...
python -u main.py
set "APP_EXIT_CODE=%ERRORLEVEL%"
goto finish

:finish
if "%APP_EXIT_CODE%" NEQ "0" (
    echo.
    echo [!] Application exited with code %APP_EXIT_CODE%.
    pause
)
