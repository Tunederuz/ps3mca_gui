@echo off
echo ========================================
echo PS3 Memory Card Manager - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.7+ and try again.
    pause
    exit /b 1
)

echo Installing/updating dependencies...
pip install -r requirements.txt

echo.
echo Building executable...
python build_exe.py

echo.
echo Build process completed!
pause
