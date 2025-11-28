@echo off
echo ================================
echo   EMG Signal Visualizer
echo ================================
echo.
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.
echo Checking dependencies...
python -m pip show matplotlib >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
)
echo.
echo Starting visualizer...
echo.
python emg_visualizer.py
pause
