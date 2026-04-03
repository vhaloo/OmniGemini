@echo off
title OmniGemini Live Assistant
color 0B

echo ==========================================
echo Starting OmniGemini
echo ==========================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please install first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python -m src.main

echo.
pause
