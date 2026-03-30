@echo off
title DeepSeek-OCR-2 Document Processor
echo ============================================
echo  DeepSeek-OCR-2 Document Processor
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Create venv if needed
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate venv
call venv\Scripts\activate.bat

:: Check for GPU
echo Detecting hardware...
python -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>nul > .device_check
set /p DEVICE=<.device_check
del .device_check 2>nul

if "%DEVICE%"=="cuda" (
    echo GPU detected! Installing GPU dependencies...
    pip install -q -r requirements-gpu.txt 2>nul
    if errorlevel 1 (
        echo GPU packages failed to install. Falling back to CPU...
        pip install -q -r requirements-cpu.txt
    )
) else (
    echo No GPU detected. Installing CPU dependencies...
    pip install -q -r requirements-cpu.txt
)

:: Install core dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

:: Check if frontend is built
if not exist "frontend\dist" (
    echo Building frontend...
    where npm >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Node.js not found. Web UI will not be available.
        echo Install Node.js from https://nodejs.org for the web interface.
        echo You can still use the CLI.
    ) else (
        cd frontend
        call npm install
        call npm run build
        cd ..
    )
)

echo.
echo ============================================
echo  Starting server...
echo  Web UI: http://127.0.0.1:8000
echo  Press Ctrl+C to stop
echo ============================================
echo.

python -m cli.main serve

pause
