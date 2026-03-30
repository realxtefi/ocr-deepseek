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

:: Step 1: Install core dependencies first (includes torch-less packages)
echo Installing core dependencies...
pip install -q -r requirements.txt

:: Step 2: Check if torch is already installed, if not install CPU version first
python -c "import torch" 2>nul
if errorlevel 1 (
    echo Installing PyTorch...
    echo Trying GPU version first...
    pip install -q torch==2.6.0 2>nul
    if errorlevel 1 (
        echo GPU torch failed. Installing CPU version...
        pip install -q -r requirements-cpu.txt
    )
)

:: Step 3: Now detect GPU with torch installed
echo Detecting hardware...
python -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" > .device_check 2>nul
set /p DEVICE=<.device_check
del .device_check 2>nul

if "%DEVICE%"=="" set DEVICE=cpu

echo Detected device: %DEVICE%

:: Step 4: If GPU available, try to install flash-attn for better performance
if "%DEVICE%"=="cuda" (
    echo GPU detected! Installing flash-attention for acceleration...
    pip install -q flash-attn==2.7.3 --no-build-isolation 2>nul
    if errorlevel 1 (
        echo flash-attn install failed ^(this is OK^). Using eager attention on GPU.
    ) else (
        echo flash-attn installed successfully.
    )
) else (
    echo Running in CPU mode.
    echo Tip: A CUDA-capable NVIDIA GPU with 6+GB VRAM will significantly speed up processing.
)

:: Step 5: Build frontend if needed
if not exist "frontend\dist" (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Node.js not found. Web UI will not be available.
        echo Install Node.js from https://nodejs.org for the web interface.
        echo You can still use the CLI.
    ) else (
        echo Building frontend...
        cd frontend
        call npm install
        call npm run build
        cd ..
    )
)

echo.
echo ============================================
echo  Device: %DEVICE%
echo  Starting server...
echo  Web UI: http://127.0.0.1:8000
echo  Press Ctrl+C to stop
echo ============================================
echo.

python -m cli.main serve

pause
