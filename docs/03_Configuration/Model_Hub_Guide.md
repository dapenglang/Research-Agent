# Model Hub Guide — Research Agent v3

**Date:** 2026-08-15
**Target:** Windows 10/11, D:/Models as model root

---

## 1. Overview

The Model Hub (`infrastructure/models/model_hub.py` and `model_validator.py`) manages VLM model loading, validation, and path resolution. Models are registered in `configs/model_registry.yaml`.

---

## 2. Recommended Directory Structure (Windows)

```
D:/Models/
├── vlm/
│   ├── llava/
│   │   └── llava-1.5-7b/
│   │       ├── config.json
│   │       ├── model*.safetensors
│   │       ├── preprocessor_config.json
│   │       └── tokenizer*
│   ├── qwen/
│   │   └── qwen2.5-vl-7b/
│   │       └── ...
│   └── internvl/
│       └── internvl2.5-8b/
│           └── ...
└── llm/
    └── (local LLM models, if using local provider)
```

---

## 3. Registered Models

From `configs/model_registry.yaml`:

| Model Key | Repo ID | VRAM Required | Path Placeholder |
|-----------|---------|---------------|-------------------|
| `llava_1_5_7b` | `llava-hf/llava-1.5-7b-hf` | 16 GB | `${DATA_ROOT}/models/vlm/llava/llava-1.5-7b` |
| `qwen2_5_vl_7b` | `Qwen/Qwen2-VL-7B-Instruct` | 16 GB | `${DATA_ROOT}/models/vlm/qwen/qwen2.5-vl-7b` |
| `internvl2_5_8b` | `OpenGVLab/InternVL2_5-8B` | 18 GB | `${DATA_ROOT}/models/vlm/internvl/internvl2.5-8b` |

**Critical for RTX A500 4GB:** All three registered models require 16-18 GB VRAM. With only 4GB VRAM, you CANNOT load these models directly. Use quantization (4-bit/8-bit) or CPU offloading, or mark as `debug_surrogate_model`.

---

## 4. Model Acquisition Methods

### 4.1 Auto-Download

If `auto_download: true` in the registry, the system will attempt to download from Hugging Face when the model is not found locally.

```powershell
# Ensure you have huggingface-cli
pip install huggingface-hub

# Set Hugging Face token (if needed)
$env:HF_TOKEN = "your_token_here"

# The system auto-downloads on first access
```

### 4.2 Manual Download

```powershell
# Using huggingface-cli
huggingface-cli download llava-hf/llava-1.5-7b-hf --local-dir D:\Models\vlm\llava\llava-1.5-7b

huggingface-cli download Qwen/Qwen2-VL-7B-Instruct --local-dir D:\Models\vlm\qwen\qwen2.5-vl-7b

huggingface-cli download OpenGVLab/InternVL2_5-8B --local-dir D:\Models\vlm\internvl\internvl2.5-8b
```

### 4.3 Offline Copy

If the target machine has no internet:
1. Download on a machine with internet
2. Copy the model directory to the target machine
3. Ensure the path matches `local_path` in `model_registry.yaml`
4. Run model validation (see below)

### 4.4 Local Loading

The system loads models using `transformers` library. The model path in `model_registry.yaml` must point to a valid Hugging Face model directory containing:
- `config.json`
- Model weight files (`.safetensors` or `.bin`)
- Tokenizer files
- Preprocessor config (for VLMs)

---

## 5. Path Configuration

Edit `configs/model_registry.yaml`:

**Option A: Use `${DATA_ROOT}` (recommended)**
Set `storage.root` in `configs/storage.yaml` to `D:/ResearchData`, then:
```yaml
local_path: "${DATA_ROOT}/models/vlm/llava/llava-1.5-7b"
```

**Option B: Use absolute paths**
```yaml
local_path: "D:/Models/vlm/llava/llava-1.5-7b"
```

---

## 6. Model Integrity Check

```powershell
conda activate research_agent_v3
cd C:\Research_Agent_v3

# Verify model files exist and are valid
python -c "
from Research_Agent_v3.infrastructure.models.model_validator import ModelValidator
import yaml

registry = yaml.safe_load(open('configs/model_registry.yaml'))
storage = yaml.safe_load(open('configs/storage.yaml'))
root = storage['storage']['root']

for name, spec in registry['models'].items():
    path = spec['local_path'].replace('\${DATA_ROOT}', root)
    import os
    exists = os.path.exists(path)
    print(f'{name}: path={path}, exists={exists}, vram_required={spec[\"vram_gb\"]}GB')
"
```

---

## 7. Model Loading Verification

```powershell
# Test loading a model (requires sufficient VRAM)
python -c "
from Research_Agent_v3.infrastructure.models.model_hub import ModelHub
hub = ModelHub()
# This will attempt to load the model
# model = hub.load_model('llava_1_5_7b')
# print('Model loaded:', model is not None)
print('ModelHub initialized')
"
```

---

## 8. VRAM Management (RTX A500 4GB)

| Model | Required VRAM | Fits 4GB? | Strategy |
|-------|---------------|-----------|----------|
| LLaVA-1.5-7B | 16 GB | No | 4-bit quantization + CPU offload |
| Qwen2.5-VL-7B | 16 GB | No | 4-bit quantization + CPU offload |
| InternVL2.5-8B | 18 GB | No | 4-bit quantization + CPU offload |

**If model cannot fit in VRAM after quantization:**
- System returns: `BLOCKED_BY_VRAM`
- Do NOT secretly swap to a smaller model
- If using a small model for debugging only: mark as `debug_surrogate_model`

---

## 9. Network Failure Handling

If Hugging Face download fails:
- Check internet connection
- Check proxy settings in `machine.yaml`
- Set `HF_TOKEN` environment variable
- Try manual download (see section 4.2)
- **DO NOT** fall back to mock. Mock is for LLM, not for VLM models.

---

## 10. Adding a New Model

1. Download the model to your models directory
2. Add an entry to `configs/model_registry.yaml`:
```yaml
  my_new_model:
    type: vlm
    source: huggingface
    repo_id: "org/model-name"
    local_path: "${DATA_ROOT}/models/vlm/my_org/my_new_model"
    auto_download: true
    allow_manual_install: true
    vram_gb: 8
```
3. Verify the model loads correctly
