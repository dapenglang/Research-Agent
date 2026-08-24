<!--
STATUS: ARCHIVED
DO NOT USE FOR CURRENT DEPLOYMENT
SEE: START_HERE.md
-->

# GPU_A First Run Checklist

**Research Agent v3 — Migration to GPU_A Server**
**Generated**: 2026-08-15

---

## Overview

This checklist guides you through setting up Research Agent v3 on a GPU_A server from scratch. Follow each step in order and verify before proceeding to the next.

---

## Step 1: Extract Project

```bash
# Copy the migration package to GPU_A
scp Research_Agent_v3_GPU_A_Migration_Package.zip user@gpu_a:/data/

# SSH to GPU_A
ssh user@gpu_a

# Navigate to target directory
cd /data

# Extract
unzip Research_Agent_v3_GPU_A_Migration_Package.zip

# Verify structure
ls Research_Agent_v3/
# Expected: adapters/ cli/ configs/ core/ docs/ infrastructure/ modules/ orchestrator/ schemas/ scripts/ tests/ environment.yml requirements.txt
```

**Verification**:
- [ ] `Research_Agent_v3/` directory exists
- [ ] `environment.yml` exists at root
- [ ] `requirements.txt` exists at root
- [ ] `configs/` directory contains 4 YAML files
- [ ] `scripts/setup_environment.sh` exists

---

## Step 2: Create Conda Environment

```bash
cd /data/Research_Agent_v3

# Option A: Use the automated setup script
bash scripts/setup_environment.sh

# Option B: Manual setup
conda create -n research_agent_v3 python=3.10 -y
conda activate research_agent_v3
```

**Verification**:
- [ ] Conda environment `research_agent_v3` created
- [ ] Python version is 3.10.x
- [ ] `conda env list` shows `research_agent_v3`

---

## Step 3: Install Dependencies

```bash
# Activate environment
conda activate research_agent_v3

# Install PyTorch with CUDA (adjust CUDA version as needed)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install all other dependencies
pip install -r requirements.txt
```

**Verification**:
- [ ] `pip install` completes without errors
- [ ] `python -c "import yaml; print('pyyaml OK')"` works
- [ ] `python -c "import numpy; print('numpy OK')"` works
- [ ] `python -c "import docx; print('python-docx OK')"` works

---

## Step 4: Detect GPU / CUDA

```bash
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
        print(f'    Memory: {torch.cuda.get_device_properties(i).total_mem / 1e9:.1f} GB')
"
```

**Verification**:
- [ ] PyTorch installed correctly
- [ ] `torch.cuda.is_available()` returns `True`
- [ ] At least 1 GPU detected
- [ ] GPU memory >= 16 GB (recommended for VLM models)

**If CUDA not available**:
- Check NVIDIA driver: `nvidia-smi`
- Check CUDA version compatibility with PyTorch
- Reinstall PyTorch with correct CUDA version

---

## Step 5: Configure Model Paths

### 5.1 Set DATA_ROOT

```bash
# Set environment variable (add to ~/.bashrc or ~/.zshrc for persistence)
export DATA_ROOT=/data/research_agent

# Create data directories
mkdir -p $DATA_ROOT/models/vlm
mkdir -p $DATA_ROOT/papers
mkdir -p $DATA_ROOT/experiments
mkdir -p $DATA_ROOT/outputs
mkdir -p $DATA_ROOT/cache
mkdir -p $DATA_ROOT/memory
```

### 5.2 Download Models

Refer to `docs/Model_Hub_Migration_Report.md` for complete model list.

**Required models** (total ~54 GB):

| Model | Size | Download Method |
|-------|------|-----------------|
| LLaVA-1.5-7B | ~13 GB | `huggingface-cli download llava-hf/llava-1.5-7b-hf` |
| Qwen2-VL-7B | ~15 GB | `huggingface-cli download Qwen/Qwen2-VL-7B-Instruct` |
| InternVL2.5-8B | ~16 GB | `huggingface-cli download OpenGVLab/InternVL2_5-8B` |

```bash
# Example: Download LLaVA-1.5-7B
huggingface-cli download llava-hf/llava-1.5-7b-hf --local-dir $DATA_ROOT/models/vlm/llava/llava-1.5-7b

# Verify model exists
ls $DATA_ROOT/models/vlm/llava/llava-1.5-7b/
# Expected: config.json, model weights, tokenizer files
```

### 5.3 Update storage.yaml

```bash
# Edit configs/storage.yaml
vim configs/storage.yaml

# Set root to use DATA_ROOT variable:
# root: "${DATA_ROOT}"
```

### 5.4 Update machine.yaml

```bash
# Edit configs/machine.yaml with GPU_A specs
vim configs/machine.yaml
```

```yaml
gpu:
  count: 1  # Update to actual count
  name: "NVIDIA A100"  # Update to actual GPU name
  memory_gb: 80  # Update to actual memory
  cuda_version: "12.1"
cpu:
  cores: 32  # Update to actual cores
  memory_gb: 128  # Update to actual RAM
```

**Verification**:
- [ ] `DATA_ROOT` environment variable set
- [ ] Model directories created
- [ ] At least 1 model downloaded
- [ ] `configs/storage.yaml` root set to `${DATA_ROOT}`
- [ ] `configs/machine.yaml` updated with GPU_A specs
- [ ] `configs/model_registry.yaml` paths use `${DATA_ROOT}`

---

## Step 6: Configure LLM Provider

### 6.1 Choose Provider

**Option A: OpenAI (recommended for quality)**
```bash
export OPENAI_API_KEY=sk-your-api-key-here
```

```yaml
# In configs/providers.yaml
active_provider: openai
openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o"
  max_tokens: 4096
  temperature: 0.7
```

**Option B: Local vLLM (recommended for cost)**
```bash
# Start vLLM server
python -m vllm.entrypoints.openai.api_server --model your-model --port 8000
```

```yaml
# In configs/providers.yaml
active_provider: local
local:
  base_url: "http://localhost:8000/v1"
  model: "your-model"
  api_key: "EMPTY"
```

**Option C: Mock (testing only — NOT for research tasks)**
```yaml
# In configs/providers.yaml
active_provider: mock
# WARNING: mock can only be used for unit_test, integration_test, development
# Research tasks (literature_analysis, innovation_generation, paper_generation, experiment_analysis) MUST use real providers
```

### 6.2 Verify Provider

```bash
python -c "
from Research_Agent_v3.infrastructure.llm.provider_factory import LLMProviderFactory
factory = LLMProviderFactory()
provider = factory.get_provider()
print(f'Active provider: {provider.__class__.__name__}')
print(f'Provider type: {provider.provider_type}')
"
```

**Verification**:
- [ ] LLM provider configured (not mock for research tasks)
- [ ] API key set (if OpenAI)
- [ ] vLLM server running (if local)
- [ ] Provider verification script runs without errors
- [ ] `validate_usage()` does not reject the configured provider

---

## Step 7: Run Environment Test

```bash
# Run the full environment verification
cd /data/Research_Agent_v3

python -c "
print('=== Environment Verification ===')

# 1. Package import
import Research_Agent_v3
print(f'[OK] Research_Agent_v3 version: {Research_Agent_v3.__version__}')

# 2. Core modules
from Research_Agent_v3.core.state.state_machine import ResearchState
print('[OK] State Machine loaded')

from Research_Agent_v3.core.contracts.module_contract import ModuleContract
print('[OK] Module Contract loaded')

# 3. Infrastructure
from Research_Agent_v3.infrastructure.storage.path_resolver import PathResolver
print('[OK] PathResolver loaded')

from Research_Agent_v3.infrastructure.storage.storage_manager import StorageManager
sm = StorageManager(data_root='/data/research_agent')
print(f'[OK] StorageManager loaded, DATA_ROOT={sm._resolver.get_variables().get(\"DATA_ROOT\", \"?\")}')

# 4. Orchestrator
from Research_Agent_v3.orchestrator import PipelineOrchestrator
print('[OK] PipelineOrchestrator loaded')

# 5. CLI
import subprocess
result = subprocess.run(['python', '-m', 'Research_Agent_v3.cli', '--help'], capture_output=True, text=True)
print(f'[OK] CLI --help: {\"usage\" in result.stdout or \"usage\" in result.stderr}')

# 6. GPU
import torch
print(f'[OK] PyTorch {torch.__version__}, CUDA available: {torch.cuda.is_available()}')

# 7. LLM Provider
from Research_Agent_v3.infrastructure.llm.provider_factory import LLMProviderFactory
factory = LLMProviderFactory()
provider = factory.get_provider()
print(f'[OK] LLM Provider: {provider.__class__.__name__}')

print('=== All checks passed ===')
"
```

**Verification**:
- [ ] All 7 checks print `[OK]`
- [ ] CUDA is available
- [ ] LLM provider is not mock (for research tasks)

---

## Step 8: Run Small Research Task (Pipeline Test)

```bash
# Run the E2E pipeline test with synthetic data
cd /data/Research_Agent_v3

python tests/test_phase_d_e2e.py
```

**Expected output**:
```
Module 10... PASS (data_origin=mixed)
Module 11... PASS (data_origin=synthetic)
Module 12... PASS (data_origin=template)
Module 13... PASS (data_origin=unknown)
Modules passed: 4/13
```

**Verification**:
- [ ] Modules 10-13 all PASS
- [ ] Output files generated in `tests/e2e_output/`
- [ ] No errors in test output

**Note**: Modules 01-09 will be SKIPPED in this test — this is expected. They require real external services (Zotero API, internet, LLM, GPU experiments). This test only validates the pipeline interface.

---

## Step 9: Enter Real Research Task

### 9.1 Create a Research Task Config

```bash
# Copy the template
cp configs/research_task.yaml.template my_research_task.yaml

# Edit with your research task details
vim my_research_task.yaml
```

```yaml
task_id: my_first_research
title: "My Research Topic"
experiment:
  method: samra
  synthetic:
    num_samples: 500
    seed: 42
  real:
    seed: 42
    checkpoint_dir: "${DATA_ROOT}/experiments/my_first_research/checkpoints"
    resume_from_checkpoint: false
analysis:
  significance_level: 0.05
  output_dir: "${DATA_ROOT}/outputs/my_first_research/analysis"
output:
  figure_table_dir: "${DATA_ROOT}/outputs/my_first_research/figures"
  paper_dir: "${DATA_ROOT}/outputs/my_first_research/paper"
  reference_dir: "${DATA_ROOT}/outputs/my_first_research/references"
llm:
  type: openai  # or local
paper:
  min_references: 30
```

### 9.2 Run the Full Pipeline

```bash
# Start the research pipeline
python -m Research_Agent_v3.cli start --task my_research_task.yaml

# Check status
python -m Research_Agent_v3.cli status --task-id my_first_research

# If interrupted, resume
python -m Research_Agent_v3.cli resume --task-id my_first_research

# If you want to re-run
python -m Research_Agent_v3.cli rerun --task-id my_first_research
```

### 9.3 Monitor Progress

The pipeline will execute modules in order:
1. Module 01-03: Literature retrieval and analysis (requires Zotero + LLM)
2. Module 04-07: Research reasoning and experiment planning (requires LLM)
3. Module 08: Synthetic experiment (requires method backend)
4. Module 09: Real experiment (requires GPU + models)
5. Module 10: Result analysis
6. Module 11: Figure and table generation
7. Module 12: Paper writing (Markdown → LaTeX → Word)
8. Module 13: Reference and supplementary

**Verification**:
- [ ] Pipeline starts without errors
- [ ] Modules 01-03 produce literature output
- [ ] Modules 04-07 produce research reasoning output
- [ ] Module 08-09 produce experiment results
- [ ] Module 10-13 produce final paper
- [ ] Paper output exists in `${DATA_ROOT}/outputs/my_first_research/paper/`

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'Research_Agent_v3'` | Run from project root, ensure `sys.path` includes parent dir |
| `CUDA out of memory` | Reduce batch size, use smaller model, or use gradient checkpointing |
| `OpenAI API key not set` | `export OPENAI_API_KEY=your_key` |
| `Mock used for research task` | Set `llm.type` to `openai` or `local` in task config |
| `Model not found` | Check `model_registry.yaml` path, ensure model downloaded |
| `Zotero API connection failed` | Check network, verify Zotero API credentials |
| `Path not found: /Users/...` | Set `DATA_ROOT` env var, update `storage.yaml` |

### Getting Help

- Review: `docs/Model_Hub_Migration_Report.md` for model setup
- Review: `docs/LLM_Provider_Preparation_Report.md` for LLM setup
- Review: `migrations/v3/Phase_E_Pipeline_Test_Report.md` for expected test results
- Review: `migrations/v3/Research_Agent_v3_Pre_Migration_Final_Report.md` for full system status

---

*GPU_A First Run Checklist — Research Agent v3*
