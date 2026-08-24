# Configuration Guide — Research Agent v3

**Date:** 2026-08-15
**All paths and fields verified from actual code.**

---

## Overview

Research Agent v3 uses YAML configuration files in `configs/`. This guide covers every file a user needs to modify.

---

## 1. machine.yaml

**Path:** `configs/machine.yaml`
**Purpose:** Describe the deployment machine's hardware and environment.

```yaml
machine:
  os: "Windows 11"              # Operating system
  python_version: "3.12"        # Python version (standard: 3.12)
  conda_env: "research_agent_v3" # Conda environment name
  cpu:
    cores: 8                    # Number of CPU cores
    architecture: "x86_64"       # CPU architecture
  ram_gb: 16                     # Total RAM in GB
  gpu:
    available: true              # Whether a GPU is available
    device: "NVIDIA RTX A500 Laptop GPU"  # GPU name
    vram_gb: 4                   # GPU VRAM in GB
    cuda_version: "12.1"         # CUDA version
  network:
    internet: true               # Internet connectivity
    proxy: ""                    # Proxy URL (empty if none)
```

**When to modify:**
- New deployment machine
- Hardware change (GPU, RAM, CPU)
- Network proxy settings

**Windows example:**
```yaml
machine:
  os: "Windows 11"
  python_version: "3.12"
  conda_env: "research_agent_v3"
  cpu:
    cores: 8
    architecture: "x86_64"
  ram_gb: 16
  gpu:
    available: true
    device: "NVIDIA RTX A500 Laptop GPU"
    vram_gb: 4
    cuda_version: "12.1"
  network:
    internet: true
    proxy: ""
```

---

## 2. storage.yaml

**Path:** `configs/storage.yaml`
**Purpose:** Define where data (models, datasets, papers, outputs) is stored.

```yaml
storage:
  root: ""                      # ROOT DATA DIRECTORY — MUST SET
  subdirs:
    models: "models"             # Model weights
    datasets: "datasets"         # Datasets
    papers: "papers"             # Downloaded papers
    experiments: "experiments"  # Experiment outputs
    external_data: "external_data"  # External data
    cache: "cache"               # Cache directory
    memory: "memory"            # Memory store
    outputs: "outputs"           # Pipeline outputs
```

**When to modify:**
- First deployment (MUST set `root`)
- Changing data storage location

**Windows example:**
```yaml
storage:
  root: "D:/ResearchData"
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

**Critical:** The `root` field must be set before running the pipeline. The path resolver (`infrastructure/storage/path_resolver.py`) resolves `${DATA_ROOT}` placeholders in other configs against this value.

---

## 3. providers.yaml

**Path:** `configs/providers.yaml`
**Purpose:** Configure LLM providers, MCP, and API integrations.

```yaml
providers:
  llm:
    default: "required"         # "required", "openai", "local", or "mock"
    mock:
      only_for:                 # Mock ONLY allowed for:
        - unit_test
        - integration_test
        - development
      prohibited_for:           # Mock PROHIBITED for:
        - literature_analysis
        - innovation_generation
        - paper_generation
        - experiment_analysis
    openai:
      api_key_env: "OPENAI_API_KEY"  # Environment variable name for API key
      model: "gpt-4"             # OpenAI model name
      temperature: 0.3           # Sampling temperature (0.0-1.0)
      max_tokens: 4096           # Max tokens per call
    local:
      endpoint: "http://localhost:8000/v1"  # Local LLM endpoint (vLLM, Ollama)
      model: "llama-3-8b"       # Local model name
  mcp:
    enabled: false              # MCP is optional, NOT a hard dependency
    servers: []                 # MCP server list
  api: {}                      # API integrations
  skills: {}                    # Skill integrations
```

**When to modify:**
- Setting up OpenAI API access
- Configuring a local LLM endpoint
- Enabling/disabling MCP

**Windows example:**
```yaml
providers:
  llm:
    default: "openai"
    mock:
      only_for:
        - unit_test
        - integration_test
        - development
      prohibited_for:
        - literature_analysis
        - innovation_generation
        - paper_generation
        - experiment_analysis
    openai:
      api_key_env: "OPENAI_API_KEY"
      model: "gpt-4"
      temperature: 0.3
      max_tokens: 4096
    local:
      endpoint: "http://localhost:8000/v1"
      model: "llama-3-8b"
  mcp:
    enabled: false
    servers: []
  api: {}
  skills: {}
```

See: [LLM Provider Guide](LLM_Provider_Guide.md)

---

## 4. model_registry.yaml

**Path:** `configs/model_registry.yaml`
**Purpose:** Register VLM models with paths, download settings, and VRAM requirements.

```yaml
models:
  llava_1_5_7b:
    type: vlm
    source: huggingface
    repo_id: "llava-hf/llava-1.5-7b-hf"
    local_path: "${DATA_ROOT}/models/vlm/llava/llava-1.5-7b"
    auto_download: true
    allow_manual_install: true
    vram_gb: 16
  qwen2_5_vl_7b:
    type: vlm
    source: huggingface
    repo_id: "Qwen/Qwen2-VL-7B-Instruct"
    local_path: "${DATA_ROOT}/models/vlm/qwen/qwen2.5-vl-7b"
    auto_download: true
    allow_manual_install: true
    vram_gb: 16
  internvl2_5_8b:
    type: vlm
    source: huggingface
    repo_id: "OpenGVLab/InternVL2_5-8B"
    local_path: "${DATA_ROOT}/models/vlm/internvl/internvl2.5-8b"
    auto_download: true
    allow_manual_install: true
    vram_gb: 18
```

**When to modify:**
- Adding new models
- Changing model paths (after setting `storage.root`)
- Removing models you don't need

**Windows example (with D:/ResearchData as storage root):**
```yaml
models:
  llava_1_5_7b:
    type: vlm
    source: huggingface
    repo_id: "llava-hf/llava-1.5-7b-hf"
    local_path: "D:/ResearchData/models/vlm/llava/llava-1.5-7b"
    auto_download: true
    allow_manual_install: true
    vram_gb: 16
```

**Note:** `${DATA_ROOT}` in `local_path` is resolved by `path_resolver.py` against `storage.root`. You can use either `${DATA_ROOT}/...` or absolute paths.

See: [Model Hub Guide](Model_Hub_Guide.md)

---

## 5. research_task.yaml (Task Config)

**Template:** `configs/research_task_template.yaml`
**Purpose:** Define a specific research task with research content, literature settings, and experiment configuration.

See: [New Research Task Guide](../02_Usage/New_Research_Task_Guide.md)

Key fields:
- `task_id` — Unique task identifier (REQUIRED)
- `title` — Research title (REQUIRED)
- `research.domain` — Research domain, e.g. `computer_vision` (REQUIRED)
- `research.keywords` — Search keywords for literature retrieval (REQUIRED)
- `research.research_question` — Core research question (REQUIRED)
- `research.target` — Target model/method/system (OPTIONAL)
- `literature.candidate_target` — Paper IDs to consider (OPTIONAL, default: auto-search)
- `literature.core_target` — Paper IDs for deep analysis (OPTIONAL, default: auto-select)
- `literature.arxiv.download_pdf` — Download PDFs from arXiv (default: true)
- `literature.arxiv.prefer_latex_analysis` — Prefer LaTeX over PDF (default: true)
- `llm.type` — LLM provider for this task (REQUIRED)
- `experiment.method` — Method backend name
- `experiment.synthetic.*` — Synthetic experiment params
- `experiment.real.*` — Real experiment params

**Important:** Do NOT use `tests/e2e_test_data/research_task.yaml` as a template for real research. It is a minimal E2E test config that lacks research content fields. Always start from `configs/research_task_template.yaml`.

---

## 6. environment.yml

**Path:** `environment.yml`
**Purpose:** Conda environment definition.

```yaml
name: research_agent_v3
channels:
  - pytorch
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.12
  - pip
  - pytorch::pytorch>=2.1.0
  - pytorch::torchvision>=0.16.0
  - pytorch::torchaudio>=2.1.0
  - pytorch::pytorch-cuda=12.1
  # ... (see actual file for full list)
```

**When to modify:** Only if a dependency conflict is found. Otherwise, use the setup scripts.

---

## 7. Configuration Summary Table

| File | Location | When to Modify | Key Fields |
|------|----------|---------------|------------|
| `machine.yaml` | `configs/` | New machine | `os`, `gpu.vram_gb`, `python_version` |
| `storage.yaml` | `configs/` | First setup | `root` (MUST set) |
| `providers.yaml` | `configs/` | LLM setup | `llm.default`, `openai.api_key_env` |
| `model_registry.yaml` | `configs/` | Model setup | `local_path` per model |
| `research_task.yaml` | User dir | New research | `task_id`, `title`, `research.domain`, `research.keywords`, `research.research_question` |
| `environment.yml` | Root | Dependency change | `python=3.12` (standard) |

---

## 8. Future Deployment Checklist

### New Windows Machine

1. Edit `machine.yaml` — Set OS, CPU, RAM, GPU
2. Edit `storage.yaml` — Set `root` to data directory
3. Edit `providers.yaml` — Set LLM provider and API key
4. Edit `model_registry.yaml` — Set model paths
5. Run `scripts/setup_environment_windows.ps1`

### New Research Task

1. Copy `configs/research_task_template.yaml` to new file
2. Edit `task_id`, `title`, `research.domain`, `research.keywords`, `research.research_question`
3. Set `llm.type` (use `openai` or `local`, NOT `mock` for production)
4. Run: `python -m Research_Agent_v3.cli.cli start --task <your_file>.yaml`
