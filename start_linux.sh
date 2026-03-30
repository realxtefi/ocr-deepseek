#!/bin/bash
echo "============================================"
echo " DeepSeek-OCR-2 Document Processor"
echo "============================================"
echo

# Parse arguments
FORCE_DEVICE="auto"
for arg in "$@"; do
    case $arg in
        --cpu)  FORCE_DEVICE="cpu" ;;
        --gpu)  FORCE_DEVICE="gpu" ;;
        --auto) FORCE_DEVICE="auto" ;;
    esac
done

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Install Python 3.10+ first."
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# =============================================
#  Determine target device
# =============================================
DEVICE="cpu"

if [ "$FORCE_DEVICE" = "cpu" ]; then
    DEVICE="cpu"
    echo "Forced device: CPU"
elif [ "$FORCE_DEVICE" = "gpu" ]; then
    DEVICE="cuda"
    echo "Forced device: GPU"
else
    # Auto-detect via nvidia-smi
    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
        DEVICE="cuda"
        echo "NVIDIA GPU detected."
    else
        echo "No NVIDIA GPU detected."
    fi
fi

# =============================================
#  Install dependencies
# =============================================

if [ -d "vendor/common" ]; then
    echo "Installing from local vendor packages (portable mode)..."

    # Common deps
    pip install -q --no-index --find-links vendor/common -r requirements.txt 2>/dev/null
    if [ $? -ne 0 ]; then
        pip install -q --no-index --find-links vendor/common --find-links vendor/cpu --find-links vendor/gpu -r requirements.txt 2>/dev/null
    fi

    # Device-specific torch
    if [ "$DEVICE" = "cuda" ]; then
        echo "Installing GPU PyTorch from vendor/gpu..."
        pip install -q --no-index --find-links vendor/gpu --find-links vendor/common torch==2.6.0 --force-reinstall 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "GPU torch failed from vendor. Falling back to CPU..."
            DEVICE="cpu"
            pip install -q --no-index --find-links vendor/cpu --find-links vendor/common torch --force-reinstall 2>/dev/null
        fi
        # flash-attn (optional)
        pip install -q --no-index --find-links vendor/gpu flash-attn 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "flash-attn not in vendor (OK). Using eager attention."
        fi
    else
        echo "Installing CPU PyTorch from vendor/cpu..."
        pip install -q --no-index --find-links vendor/cpu --find-links vendor/common torch --force-reinstall 2>/dev/null
    fi
else
    echo "Installing from internet..."

    # Core deps
    pip install -q -r requirements.txt

    # Torch
    if [ "$DEVICE" = "cuda" ]; then
        echo "Installing GPU PyTorch..."
        pip install -q torch==2.6.0 --force-reinstall 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "GPU torch failed. Falling back to CPU..."
            DEVICE="cpu"
            pip install -q -r requirements-cpu.txt
        fi
        pip install -q flash-attn==2.7.3 --no-build-isolation 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "flash-attn install failed (OK). Using eager attention."
        fi
    else
        echo "Installing CPU PyTorch..."
        pip install -q -r requirements-cpu.txt
    fi
fi

# =============================================
#  Post-install: verify and launch
# =============================================

# Final device verification
DEVICE=$(python3 -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null || echo "cpu")
echo "Final device: $DEVICE"

# Build frontend if needed
if [ ! -d "frontend/dist" ]; then
    if command -v npm &> /dev/null; then
        echo "Building frontend..."
        cd frontend && npm install && npm run build && cd ..
    else
        echo "WARNING: Node.js not found. Web UI won't be available."
        echo "Install Node.js for the web interface. CLI still works."
    fi
fi

echo
echo "============================================"
echo " Device: $DEVICE"
echo " Starting server..."
echo " Web UI: http://127.0.0.1:8000"
echo " Press Ctrl+C to stop"
echo "============================================"
echo

python -m cli.main --device $DEVICE serve
