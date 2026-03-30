@echo off
title DeepSeek-OCR-2 Document Processor
echo ============================================
echo  DeepSeek-OCR-2 Document Processor
echo ============================================
echo.

:: Parse arguments
set FORCE_DEVICE=auto
:parse_args
if "%~1"=="" goto :done_args
if "%~1"=="--cpu" set FORCE_DEVICE=cpu
if "%~1"=="--gpu" set FORCE_DEVICE=gpu
if "%~1"=="--auto" set FORCE_DEVICE=auto
shift
goto :parse_args
:done_args

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

:: =============================================
::  Determine target device
:: =============================================
if "%FORCE_DEVICE%"=="cpu" (
    set DEVICE=cpu
    echo Forced device: CPU
    goto :install_deps
)
if "%FORCE_DEVICE%"=="gpu" (
    set DEVICE=cuda
    echo Forced device: GPU
    goto :install_deps
)

:: Auto-detect: check nvidia-smi (hardware level, no torch needed)
set DEVICE=cpu
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    set DEVICE=cuda
    echo NVIDIA GPU detected.
) else (
    echo No NVIDIA GPU detected.
)

:install_deps
:: =============================================
::  Install dependencies
:: =============================================

:: Check if vendor/ exists (portable mode)
if exist "vendor\common" (
    echo Installing from local vendor packages ^(portable mode^)...
    goto :portable_install
) else (
    echo Installing from internet...
    goto :online_install
)

:: ----- PORTABLE INSTALL (from vendor/) -----
:portable_install

:: Install torch + torchvision FIRST (device-specific)
if "%DEVICE%"=="cuda" (
    echo Installing GPU PyTorch + torchvision from vendor\gpu...
    pip install -q --no-index --find-links vendor\gpu --find-links vendor\common torch==2.6.0 torchvision==0.21.0 --force-reinstall 2>nul
    if errorlevel 1 (
        echo GPU torch install failed from vendor. Falling back to CPU...
        set DEVICE=cpu
        pip install -q --no-index --find-links vendor\cpu --find-links vendor\common torch torchvision --force-reinstall 2>nul
    )
    :: flash-attn (optional)
    pip install -q --no-index --find-links vendor\gpu flash-attn 2>nul
    if errorlevel 1 (
        echo flash-attn not available in vendor ^(OK^). Using eager attention.
    )
) else (
    echo Installing CPU PyTorch + torchvision from vendor\cpu...
    pip install -q --no-index --find-links vendor\cpu --find-links vendor\common torch torchvision --force-reinstall 2>nul
)

:: Now install remaining deps (search all vendor dirs for any shared packages)
echo Installing remaining dependencies from vendor...
pip install -q --no-index --find-links vendor\common --find-links vendor\cpu --find-links vendor\gpu -r requirements.txt 2>nul

goto :post_install

:: ----- ONLINE INSTALL (pip from internet) -----
:online_install

:: Core deps
pip install -q -r requirements.txt

:: Torch
if "%DEVICE%"=="cuda" (
    echo Installing GPU PyTorch...
    pip install -q torch==2.6.0 --force-reinstall 2>nul
    if errorlevel 1 (
        echo GPU torch failed. Falling back to CPU...
        set DEVICE=cpu
        pip install -q -r requirements-cpu.txt
    )
    :: flash-attn
    pip install -q flash-attn==2.7.3 --no-build-isolation 2>nul
    if errorlevel 1 (
        echo flash-attn install failed ^(OK^). Using eager attention.
    )
) else (
    echo Installing CPU PyTorch...
    pip install -q -r requirements-cpu.txt
)

goto :post_install

:: =============================================
::  Post-install: verify and launch
:: =============================================
:post_install

:: Verify final device
python -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" > .device_check 2>nul
set /p DEVICE=<.device_check
del .device_check 2>nul
if "%DEVICE%"=="" set DEVICE=cpu

echo Final device: %DEVICE%

:: Build frontend if needed
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

python -m cli.main --device %DEVICE% serve

pause
