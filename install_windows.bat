@echo off
title OmniGemini Installer
color 0A

echo ==========================================
echo    OmniGemini Windows Auto-Installer
echo ==========================================
echo.

cd /d "%~dp0"

:: Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Creating Python Virtual Environment (venv)...
if not exist "venv\" (
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        color 0C
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists. Skipping creation.
)

echo.
echo [2/3] Activating Virtual Environment and Upgrading PIP...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1

echo.
echo [3/3] Installing Required Dependencies...
echo This may take a few minutes depending on your internet connection.
pip install google-genai sounddevice numpy opencv-python mss Pillow PyQt6 qasync rich
if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo [ERROR] Failed to install dependencies. Please check your internet connection or Python setup.
    pause
    exit /b 1
)

color 0A
echo.

echo ==========================================
echo    Installation Completed Successfully!
echo ==========================================
echo.

echo You can now launch OmniGemini by double-clicking:
echo "Launch OmniGemini.bat"
echo.
set /p START_NOW="Do you want to launch OmniGemini now? (Y/N): "
if /I "%START_NOW%"=="Y" (
    call "Launch OmniGemini.bat"
) else (
    pause
)
