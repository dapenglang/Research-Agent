#!/bin/bash
# ============================================================
# Research Agent v3 — Environment Setup Script
# ============================================================
# Creates conda environment and installs all dependencies.
# Tested on: Ubuntu 22.04, CUDA 12.1, Python 3.12
# ============================================================

set -e

ENV_NAME="research_agent_v3"
PYTHON_VERSION="3.12"

echo "================================================"
echo "  Research Agent v3 — Environment Setup"
echo "================================================"
echo ""

# ------------------------------------------------
# Step 1: Check conda
# ------------------------------------------------
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found. Please install Miniconda or Anaconda first."
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "[1/5] Conda found: $(conda --version)"

# ------------------------------------------------
# Step 2: Create conda environment
# ------------------------------------------------
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "[2/5] Conda environment '${ENV_NAME}' already exists. Removing..."
    conda env remove -n "${ENV_NAME}" -y
fi

echo "[2/5] Creating conda environment '${ENV_NAME}' (Python ${PYTHON_VERSION})..."
conda create -n "${ENV_NAME}" "python=${PYTHON_VERSION}" -y

# ------------------------------------------------
# Step 3: Activate and install
# ------------------------------------------------
echo "[3/5] Installing PyTorch (CUDA 12.1)..."
conda run -n "${ENV_NAME}" pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo "[4/5] Installing Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

conda run -n "${ENV_NAME}" pip install -r "${PROJECT_ROOT}/requirements.txt"

# ------------------------------------------------
# Step 5: Verify
# ------------------------------------------------
echo "[5/5] Verifying installation..."
echo ""
echo "  Python:        $(conda run -n ${ENV_NAME} python --version)"
echo "  PyTorch:       $(conda run -n ${ENV_NAME} python -c 'import torch; print(torch.__version__)')"
echo "  CUDA avail:    $(conda run -n ${ENV_NAME} python -c 'import torch; print(torch.cuda.is_available())')"
echo "  Transformers:  $(conda run -n ${ENV_NAME} python -c 'import transformers; print(transformers.__version__)')"
echo "  YAML:          $(conda run -n ${ENV_NAME} python -c 'import yaml; print(yaml.__version__)')"
echo "  OpenAI:        $(conda run -n ${ENV_NAME} python -c 'import openai; print(openai.__version__)')"
echo ""

# Check GPU
GPU_COUNT=$(conda run -n "${ENV_NAME}" python -c "import torch; print(torch.cuda.device_count())" 2>/dev/null || echo "0")
if [ "$GPU_COUNT" -gt "0" ]; then
    echo "  GPU detected:  $(conda run -n ${ENV_NAME} python -c 'import torch; print(torch.cuda.get_device_name(0))')"
    echo "  CUDA version:  $(conda run -n ${ENV_NAME} python -c 'import torch; print(torch.version.cuda)')"
else
    echo "  WARNING: No GPU detected. Real experiments will not run."
fi

echo ""
echo "================================================"
echo "  Environment setup complete!"
echo "  Activate with:  conda activate ${ENV_NAME}"
echo "  Project root:   ${PROJECT_ROOT}"
echo "================================================"
