#!/bin/bash
echo "============================================"
echo " DeepSeek-OCR-2 Document Processor"
echo "============================================"
echo

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

# Step 1: Install core dependencies first
echo "Installing core dependencies..."
pip install -q -r requirements.txt

# Step 2: Detect NVIDIA GPU at hardware level (works without torch)
HAS_NVIDIA=0
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi &> /dev/null && HAS_NVIDIA=1
fi

# Step 3: Check current torch status
TORCH_CUDA=$(python3 -c "import torch; print('1' if torch.cuda.is_available() else '0')" 2>/dev/null || echo "none")

# Step 4: Install or upgrade torch based on hardware vs current install
if [ "$HAS_NVIDIA" = "1" ]; then
    # GPU machine
    if [ "$TORCH_CUDA" = "1" ]; then
        echo "PyTorch with CUDA already installed."
    else
        if [ "$TORCH_CUDA" = "0" ]; then
            echo "CPU-only PyTorch detected on GPU machine. Upgrading to CUDA version..."
        else
            echo "Installing PyTorch with CUDA support..."
        fi
        pip install -q torch==2.6.0 --force-reinstall 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "GPU torch install failed. Falling back to CPU version..."
            pip install -q -r requirements-cpu.txt
        fi
    fi
else
    # CPU-only machine
    if [ "$TORCH_CUDA" = "none" ]; then
        echo "No NVIDIA GPU detected. Installing CPU PyTorch..."
        pip install -q -r requirements-cpu.txt
    else
        echo "PyTorch already installed."
    fi
fi

# Step 5: Final device detection
DEVICE=$(python3 -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null || echo "cpu")
echo "Detected device: $DEVICE"

# Step 6: If GPU, try flash-attn
if [ "$DEVICE" = "cuda" ]; then
    python3 -c "import flash_attn" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Installing flash-attention for GPU acceleration..."
        pip install -q flash-attn==2.7.3 --no-build-isolation 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "flash-attn installed successfully."
        else
            echo "flash-attn install failed (this is OK). Using eager attention on GPU."
        fi
    else
        echo "flash-attn already installed."
    fi
else
    echo "Running in CPU mode."
    echo "Tip: A CUDA-capable NVIDIA GPU with 6+GB VRAM will significantly speed up processing."
fi

# Step 7: Build frontend if needed
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

python -m cli.main serve
