# ============================================================
# Research Agent v3 — Windows Environment Setup Script (PowerShell)
# ============================================================
# Creates conda environment and installs all dependencies.
# Target: Windows 10/11, Python 3.12, NVIDIA RTX A500 Laptop GPU 4GB
# ============================================================

$ENV_NAME = "research_agent_v3"
$PYTHON_VERSION = "3.12"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Research Agent v3 - Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------
# Step 0: Initialize conda for PowerShell
# ------------------------------------------------
# Conda PowerShell module requires CONDA_EXE to be set.
# Auto-detect common install locations.
if (-not $Env:CONDA_EXE) {
    $condaCandidates = @(
        "$Env:USERPROFILE\miniconda3\Scripts\conda.exe",
        "$Env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$Env:LOCALAPPDATA\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\anaconda3\Scripts\conda.exe",
        "D:\anaconda3\Scripts\conda.exe",
        "D:\miniconda3\Scripts\conda.exe"
    )
    foreach ($candidate in $condaCandidates) {
        if (Test-Path $candidate) {
            $Env:CONDA_EXE = $candidate
            break
        }
    }
}

if (-not $Env:CONDA_EXE -or -not (Test-Path $Env:CONDA_EXE)) {
    # Last resort: search Get-Command
    $condaCmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($condaCmd -and $condaCmd.Source) {
        $condaDir = Split-Path -Parent (Split-Path -Parent $condaCmd.Source)
        $candidate = Join-Path $condaDir "Scripts\conda.exe"
        if (Test-Path $candidate) {
            $Env:CONDA_EXE = $candidate
        }
    }
}

if (-not $Env:CONDA_EXE -or -not (Test-Path $Env:CONDA_EXE)) {
    Write-Host "ERROR: conda.exe not found. Please install Miniconda or Anaconda first." -ForegroundColor Red
    Write-Host "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
}

Write-Host "[0/5] Conda executable: $Env:CONDA_EXE"

# Initialize conda PowerShell hook so 'conda' commands work properly
$condaHook = & $Env:CONDA_EXE "shell.powershell" "hook" 2>$null
if ($condaHook) {
    $condaHook | Out-String | Invoke-Expression
}

# ------------------------------------------------
# Step 1: Check conda
# ------------------------------------------------
Write-Host "[1/5] Conda version: $(& $Env:CONDA_EXE --version 2>$null)"

# ------------------------------------------------
# Step 2: Create conda environment
# ------------------------------------------------
$envList = & $Env:CONDA_EXE env list 2>$null
if ($envList -match $ENV_NAME) {
    Write-Host "[2/5] Conda environment '$ENV_NAME' already exists. Removing..."
    & $Env:CONDA_EXE env remove -n $ENV_NAME -y 2>&1 | Out-Null
}

Write-Host "[2/5] Creating conda environment '$ENV_NAME' (Python $PYTHON_VERSION)..."
& $Env:CONDA_EXE create -n $ENV_NAME "python=$PYTHON_VERSION" -y 2>&1 | ForEach-Object { Write-Host $_ }

# ------------------------------------------------
# Step 3: Install PyTorch (CUDA 12.1)
# ------------------------------------------------
Write-Host "[3/5] Installing PyTorch (CUDA 12.1)..."
& $Env:CONDA_EXE run -n $ENV_NAME --no-capture-output pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# ------------------------------------------------
# Step 4: Install Python dependencies
# ------------------------------------------------
Write-Host "[4/5] Installing Python dependencies..."
& $Env:CONDA_EXE run -n $ENV_NAME --no-capture-output pip install -r "$PROJECT_ROOT\requirements.txt"

# ------------------------------------------------
# Step 5: Verify
# ------------------------------------------------
Write-Host "[5/5] Verifying installation..."
Write-Host ""
$pyVer = & $Env:CONDA_EXE run -n $ENV_NAME python --version 2>&1
Write-Host "  Python:        $pyVer"
$torchVer = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import torch; print(torch.__version__)" 2>&1
Write-Host "  PyTorch:       $torchVer"
$cudaAvail = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import torch; print(torch.cuda.is_available())" 2>&1
Write-Host "  CUDA avail:    $cudaAvail"
$tfVer = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import transformers; print(transformers.__version__)" 2>&1
Write-Host "  Transformers:  $tfVer"
$yamlVer = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import yaml; print(yaml.__version__)" 2>&1
Write-Host "  YAML:          $yamlVer"
$openaiVer = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import openai; print(openai.__version__)" 2>&1
Write-Host "  OpenAI:        $openaiVer"
Write-Host ""

# Check GPU
$gpuCount = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import torch; print(torch.cuda.device_count())" 2>&1
if ($gpuCount -match "^(\d+)$" -and [int]$Matches[1] -gt 0) {
    $gpuName = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import torch; print(torch.cuda.get_device_name(0))" 2>&1
    Write-Host "  GPU detected:  $gpuName"
    $cudaVer = & $Env:CONDA_EXE run -n $ENV_NAME python -c "import torch; print(torch.version.cuda)" 2>&1
    Write-Host "  CUDA version:  $cudaVer"
} else {
    Write-Host "  GPU count:     $gpuCount"
    Write-Host "  WARNING: No GPU detected. Real experiments will not run." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Environment setup complete!" -ForegroundColor Green
Write-Host "  Activate with:  conda activate $ENV_NAME" -ForegroundColor Green
Write-Host "  Project root:   $PROJECT_ROOT" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
