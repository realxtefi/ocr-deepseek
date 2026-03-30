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

# Check for GPU
DEVICE=$(python3 -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null || echo "cpu")

if [ "$DEVICE" = "cuda" ]; then
    echo "GPU detected! Installing GPU dependencies..."
    pip install -q -r requirements-gpu.txt 2>/dev/null || {
        echo "GPU packages failed. Falling back to CPU..."
        pip install -q -r requirements-cpu.txt
    }
else
    echo "No GPU detected. Installing CPU dependencies..."
    pip install -q -r requirements-cpu.txt
fi

# Install core dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

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
echo " Starting server..."
echo " Web UI: http://127.0.0.1:8000"
echo " Press Ctrl+C to stop"
echo "============================================"
echo

python -m cli.main serve
