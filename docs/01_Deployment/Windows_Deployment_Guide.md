# Windows Deployment Guide — Research Agent v3

**Target Platform:** Windows 10/11, Python 3.12, NVIDIA RTX A500 Laptop GPU 4GB
**Date:** 2026-08-15

---

## 1. Pre-Installation Checklist

| Item | Required | Notes |
|------|----------|-------|
| Windows 10 or 11 | Yes | 64-bit |
| Miniconda or Anaconda | Yes | [Install](https://docs.conda.io/en/latest/miniconda.html) |
| NVIDIA GPU driver | Recommended | For CUDA support (RTX A500 Laptop GPU) |
| 20GB free disk space | Yes | For env + models + data |
| Internet connection | Yes | For initial setup and literature retrieval |
| OpenAI API key | For production | Set as `OPENAI_API_KEY` env var. Or use local LLM. |

---

## 2. Step-by-Step Installation

### Step 1: Extract the Release ZIP

```powershell
# Extract Research_Agent_v3_Windows_Release_v3.zip to:
#   C:\Research_Agent_v3
# Or any path without spaces (recommended)
```

### Step 2: Open PowerShell

```powershell
# Open PowerShell as Administrator (recommended for conda)
# Navigate to the extracted directory
cd C:\Research_Agent_v3
```

### Step 3: Create Conda Environment

```powershell
# Option A: Use the automated script
powershell -ExecutionPolicy Bypass -File scripts\setup_environment_windows.ps1

# Option B: Manual setup
conda create -n research_agent_v3 python=3.12 -y
conda activate research_agent_v3
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### Step 4: Verify Installation

```powershell
conda activate research_agent_v3
python --version          # Should show Python 3.12.x
python -c "import torch; print(torch.__version__)"
python -c "import torch; print(torch.cuda.is_available())"  # Should show True
python -c "import transformers; print(transformers.__version__)"
python -c "import yaml; print(yaml.__version__)"
```

If `torch.cuda.is_available()` returns `False`:
- Check NVIDIA driver is installed and up to date
- Verify you have an NVIDIA GPU
- CUDA 12.1 compatible driver is required

### Step 5: Configure Storage Paths

Edit `configs/storage.yaml`:

```yaml
storage:
  root: "D:/ResearchData"    # Your data root directory
  subdirs:
    models: "models"
    datasets: "datasets"
    papers: "papers"
    experiments: "experiments"
    external_data: "external_data"
    cache: "cache"
    memory: "memory"
    outputs: "outputs"
```

Create the directory:
```powershell
mkdir D:\ResearchData
```

### Step 6: Configure Machine Info

Edit `configs/machine.yaml`:

```yaml
machine:
  os: "Windows 11"
  python_version: "3.12"
  conda_env: "research_agent_v3"
  cpu:
    cores: 8                    # Your CPU core count
    architecture: "x86_64"
  ram_gb: 16                     # Your RAM in GB
  gpu:
    available: true
    device: "NVIDIA RTX A500 Laptop GPU"
    vram_gb: 4
    cuda_version: "12.1"
  network:
    internet: true
    proxy: ""                   # Set if behind a proxy
```

### Step 7: Configure LLM Provider

Edit `configs/providers.yaml`:

```yaml
providers:
  llm:
    default: "openai"           # or "local"
    openai:
      api_key_env: "OPENAI_API_KEY"
      model: "gpt-4"
      temperature: 0.3
      max_tokens: 4096
    local:
      endpoint: "http://localhost:8000/v1"
      model: "llama-3-8b"
```

Set the API key:
```powershell
# Temporary (current session):
$env:OPENAI_API_KEY = "sk-your-key-here"

# Permanent:
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")
```

**CRITICAL:** Mock is only for testing. Never use Mock for production research tasks.
See: [LLM Provider Guide](../03_Configuration/LLM_Provider_Guide.md)

### Step 8: Configure Model Registry

Edit `configs/model_registry.yaml` — set paths under your data root:

```yaml
models:
  llava_1_5_7b:
    local_path: "D:/ResearchData/models/vlm/llava/llava-1.5-7b"
    # ... other fields remain
  qwen2_5_vl_7b:
    local_path: "D:/ResearchData/models/vlm/qwen/qwen2.5-vl-7b"
  internvl2_5_8b:
    local_path: "D:/ResearchData/models/vlm/internvl/internvl2.5-8b"
```

See: [Model Hub Guide](../03_Configuration/Model_Hub_Guide.md)

### Step 9: Environment Validation

```powershell
conda activate research_agent_v3
cd C:\Research_Agent_v3

# Verify imports
python -c "from Research_Agent_v3 import core, infrastructure, modules, adapters; print('All imports OK')"

# Verify CLI
python -m Research_Agent_v3.cli.cli --help

# Verify config loading
python -c "import yaml; c=yaml.safe_load(open('configs/machine.yaml')); print('machine.yaml OK:', c['machine']['python_version'])"
```

### Step 10: CLI Validation

```powershell
# Show available commands
python -m Research_Agent_v3.cli.cli --help

# Expected output:
#   start   — Launch a new research task from scratch
#   resume  — Resume an interrupted/paused task
#   rerun   — Re-execute from a specific module (--from MODULE_ID)
#   status  — Show current pipeline state
```

### Step 11: Small Pipeline Test (Smoke Test)

```powershell
# Run the E2E test (uses mock LLM, synthetic data — OK for testing)
python -m pytest tests/test_phase_d_e2e.py -v
```

Expected: modules 10-13 pass, 11/11 constraint checks pass.

### Step 12: Synthetic Experiment Test

```powershell
# Create a test task (copy template)
copy tests\e2e_test_data\research_task.yaml my_first_task.yaml

# Edit my_first_task.yaml:
#   - Set title to your research topic
#   - Set llm.type to "openai" (NOT "mock" for real research)
#   - For testing only: keep llm.type as "mock"

# Start the pipeline
python -m Research_Agent_v3.cli.cli start --task my_first_task.yaml

# Check status
python -m Research_Agent_v3.cli.cli status --task my_first_task.yaml
```

---

## 3. Experiment Rules

### 3.1 Synthetic Experiment (LEVEL B)

Synthetic experiments use generated data based on the method's theoretical model.

**MUST be complete:**
- Research hypothesis
- Method specification
- Mathematical formulation
- Baselines
- Datasets (synthetic)
- Metrics
- Ablation study
- Robustness analysis
- Statistical tests
- Claim-evidence plan

**MUST:**
- `data_origin=synthetic` on all output files
- Tag all results as synthetic in provenance

**MUST NOT:**
- Present synthetic results as real
- Skip statistical analysis
- Use synthetic results to make real-world claims

### 3.2 Small-scale Real Experiment (LEVEL C)

Real experiments on the RTX A500 4GB VRAM with reduced scale.

**MUST remain complete (full-scale):**
- Target model (architecture, method, loss function)
- Method specification
- Loss function
- Preprocessing pipeline
- Baseline implementation
- Metric computation
- Experiment definition

**ALLOWED to reduce:**
- Number of samples
- Number of epochs / steps
- Batch size
- Number of seeds
- Evaluation subset size

**ALLOWED techniques (to fit 4GB VRAM):**
- FP16 / BF16 mixed precision
- 4-bit / 8-bit quantization
- CPU offloading
- Gradient checkpointing
- LoRA / QLoRA / PEFT
- Backbone freezing

**If 4GB VRAM cannot load the target model:**
- The system returns: `BLOCKED_BY_VRAM`
- You must NOT secretly swap to a smaller model
- Mark debug-only small models as: `debug_surrogate_model`

### 3.3 Publication-scale Real Experiment (LEVEL D)

Full-scale real experiments. **NOT supported on RTX A500 4GB.** Future: migrate to Linux + RTX 3090 24GB.

---

## 4. Capability Levels Summary

| Level | Description | What You Can Do | RTX A500 4GB |
|-------|-------------|-----------------|--------------|
| **A** | Full Software Pipeline | Run all 13 modules with mock LLM and synthetic data | **Supported** |
| **B** | Full-design Synthetic Research | Complete method design + synthetic experiments with statistical analysis | **Supported** |
| **C** | Small-scale Real Experiment | Real model experiments with reduced scale (samples, epochs, batch size) | **Conditional** |
| **D** | Publication-scale Real Experiment | Full-scale real experiments for publication | **Not supported** (future: RTX 3090) |

---

## 5. Output Locations

After running a pipeline, outputs are saved to:

```
output/                          (or your --output-root)
├── 01_literature_retrieval/
│   ├── literature_manifest.json
│   ├── paper_metadata.jsonl
│   └── download_queue.json
├── 02_source_acquisition/
│   ├── papers/<paper_id>/
│   │   ├── metadata.json
│   │   ├── normalized/paper.md
│   │   ├── equations.json
│   │   ├── figures.json
│   │   ├── tables.json
│   │   ├── citations.json
│   │   └── provenance.json
├── 03_literature_intelligence/
│   ├── paper_analysis.json
│   └── literature_analysis_index.jsonl
├── ...
├── 11_figure_table/
│   ├── figures/*.svg
│   ├── figures/source_data/
│   ├── tables/*.xlsx
│   └── captions/captions.yaml
├── 12_paper_writing/
│   ├── paper/paper.md
│   ├── paper/latex/main.tex
│   └── paper/word/paper.docx
└── 13_reference_supplementary/
    ├── references.bib
    ├── citation_validation_report.md
    ├── supplementary.tex
    └── supplementary.docx
```

State files (for resume/rerun) are saved to:
```
state/                           (or your --state-root)
├── checkpoints/
├── research_state.json
└── ...
```

---

## 6. Checkpoint & Resume

```powershell
# If a pipeline is interrupted (e.g. GPU OOM, network timeout):
python -m Research_Agent_v3.cli.cli resume --task my_task.yaml

# To rerun from a specific module (e.g. redo figure generation):
python -m Research_Agent_v3.cli.cli rerun --task my_task.yaml --from 11

# To check current state:
python -m Research_Agent_v3.cli.cli status --task my_task.yaml
```

The state machine supports:
- `EXPERIMENT_RUNNING` — experiment in progress
- `EXPERIMENT_INTERRUPTED` — experiment was interrupted, can resume
- `EXPERIMENT_RESUMING` — experiment is resuming from checkpoint

---

## 7. Windows-Specific Notes

### 7.1 Path Separators

- Config files (`*.yaml`): Use forward slashes `/` (YAML standard)
- PowerShell commands: Use backslashes `\` or forward slashes `/`
- Python code: Uses `pathlib.Path`, handles both separators

### 7.2 PowerShell vs Bash

This project includes two setup scripts:
- `scripts/setup_environment_windows.ps1` — for Windows PowerShell
- `scripts/setup_environment.sh` — for Linux/macOS Bash

**On Windows, always use the `.ps1` script.**

### 7.3 Long Path Support

If you encounter "path too long" errors:
```powershell
# Enable long paths in Windows
git config --system core.longpaths true
# Or in Registry: HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1
```

### 7.4 CUDA Toolkit

- PyTorch installs CUDA runtime automatically via `--index-url https://download.pytorch.org/whl/cu121`
- You do NOT need to install the full CUDA Toolkit separately
- You DO need the NVIDIA display driver (compatible with CUDA 12.1)

---

## 8. Troubleshooting

See: [Troubleshooting Guide](../04_Troubleshooting/Troubleshooting_Guide.md)
