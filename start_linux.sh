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

# Step 2: Check if torch is installed, if not install it
python3 -c "import torch" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing PyTorch..."
    echo "Trying GPU version first..."
    pip install -q torch==2.6.0 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "GPU torch failed. Installing CPU version..."
        pip install -q -r requirements-cpu.txt
    fi
fi

# Step 3: Now detect GPU with torch installed
DEVICE=$(python3 -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null || echo "cpu")
echo "Detected device: $DEVICE"

# Step 4: If GPU, try installing flash-attn
if [ "$DEVICE" = "cuda" ]; then
    echo "GPU detected! Installing flash-attention for acceleration..."
    pip install -q flash-attn==2.7.3 --no-build-isolation 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "flash-attn installed successfully."
    else
        echo "flash-attn install failed (this is OK). Using eager attention on GPU."
    fi
else
    echo "Running in CPU mode."
    echo "Tip: A CUDA-capable NVIDIA GPU with 6+GB VRAM will significantly speed up processing."
fi

# Step 5: Build frontend if needed
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
