@echo off
title SpeakThat Windows Text Reader
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo Starting SpeakThat using .venv...
    ".venv\Scripts\python.exe" main.py
) else (
    echo Starting SpeakThat using system Python...
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%.
    pause
)

