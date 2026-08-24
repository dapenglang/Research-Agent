<!--
STATUS: ARCHIVED
DO NOT USE FOR CURRENT DEPLOYMENT
SEE: START_HERE.md
-->

# Research Agent v3 — GPU_A Migration Guide

**Version**: 3.0.0
**Generated**: 2026-08-15
**Package**: Research_Agent_v3_GPU_A_Migration_Package.zip

---

## What's Inside

```
Research_Agent_v3_GPU_A_Migration_Package.zip
├── Research_Agent_v3/          # Full source code (107 Python files)
│   ├── adapters/               # SAMRA adapter + method backend interface
│   ├── cli/                    # CLI entry point (start/resume/rerun/status)
│   ├── configs/                # machine.yaml, storage.yaml, providers.yaml, model_registry.yaml
│   ├── core/                   # State machine, contracts, provenance, validation
│   ├── docs/                   # GPU_A_First_Run_Checklist.md, README_GPU_A.md
│   ├── infrastructure/         # Storage, LLM, models, memory, validation
│   ├── modules/                # 13 modules (01-13)
│   ├── orchestrator/           # PipelineOrchestrator
│   ├── schemas/                # JSON schemas for validation
│   ├── scripts/                # setup_environment.sh
│   ├── tests/                  # E2E test + unit tests
│   ├── environment.yml         # Conda environment definition
│   └── requirements.txt        # Pip requirements
├── configs/                    # Reference config copies
├── scripts/                    # Reference script copies
├── docs/                       # Documentation
├── tests/                      # Test files
├── environment.yml             # Conda environment
├── requirements.txt            # Pip requirements
├── README_GPU_A.md             # This file
└── GPU_A_First_Run_Checklist.md  # Step-by-step setup guide
```

---

## Quick Start

```bash
# 1. Extract
unzip Research_Agent_v3_GPU_A_Migration_Package.zip
cd Research_Agent_v3/

# 2. Setup environment
bash scripts/setup_environment.sh
conda activate research_agent_v3

# 3. Set environment variables
export DATA_ROOT=/data/research_agent
export OPENAI_API_KEY=your_key  # if using OpenAI

# 4. Update configs
vim configs/machine.yaml   # Set GPU_A hardware specs
vim configs/storage.yaml   # Set root: "${DATA_ROOT}"

# 5. Download models (see Model_Hub_Migration_Report.md)
huggingface-cli download llava-hf/llava-1.5-7b-hf --local-dir $DATA_ROOT/models/vlm/llava/llava-1.5-7b

# 6. Run pipeline test
python tests/test_phase_d_e2e.py

# 7. Run real research task
python -m Research_Agent_v3.cli start --task your_research_task.yaml
```

**For detailed instructions, see `GPU_A_First_Run_Checklist.md`.**

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | 1x 16GB VRAM | 1x 80GB (A100) |
| CUDA | 11.8+ | 12.1 |
| RAM | 32 GB | 128 GB |
| Storage | 100 GB free | 500 GB SSD |
| Python | 3.10 | 3.10 |
| OS | Linux | Ubuntu 22.04 |

---

## Module Overview

| Module | Name | GPU Required | External Service |
|--------|------|:---:|-------------------|
| 01 | Literature Retrieval | No | Zotero API / Web |
| 02 | Source Acquisition | No | Internet (paper download) |
| 03 | Literature Intelligence | No | LLM API |
| 04 | Research Landscape | No | LLM API |
| 05 | Innovation Reasoning | No | LLM API |
| 06 | Theory & Method | No | LLM API |
| 07 | Experiment Planning | No | LLM API |
| 08 | Synthetic Experiment Engine | Optional | Method backend |
| 09 | Real Experiment Engine | **Yes** | GPU + PyTorch + models |
| 10 | Result Analysis | No | — |
| 11 | Figure & Table Generation | No | matplotlib |
| 12 | Paper Writing | No | LLM API (optional) |
| 13 | Reference & Supplementary | No | Module 01 output |

---

## Key Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| GPU_A First Run Checklist | `docs/GPU_A_First_Run_Checklist.md` | Step-by-step setup |
| System Freeze Report | `migrations/v3/Research_Agent_v3_System_Freeze_Report.md` | System status |
| Pipeline Test Report | `migrations/v3/Phase_E_Pipeline_Test_Report.md` | E2E test results |
| Portability Report | `migrations/v3/Phase_E_Portability_Report.md` | Path validation |
| Config Report | `migrations/v3/Phase_E_Config_Report.md` | Config validation |
| Environment Report | `migrations/v3/Environment_Reproduction_Report.md` | Environment setup |
| Model Hub Report | `migrations/v3/Model_Hub_Migration_Report.md` | Model download guide |
| LLM Provider Report | `migrations/v3/LLM_Provider_Preparation_Report.md` | LLM setup guide |
| Final Report | `migrations/v3/Research_Agent_v3_Pre_Migration_Final_Report.md` | Complete migration summary |

---

## Critical Warnings

1. **Mock is for testing only.** Research tasks (literature_analysis, innovation_generation, paper_generation, experiment_analysis) MUST use real LLM providers. The `validate_usage()` function enforces this.

2. **This package does NOT contain real experiment results.** All test results on the development machine used synthetic/mock data. Real scientific validation requires GPU_A with actual models, data, and LLM providers.

3. **Models are NOT included in this package.** You must download models separately. See `Model_Hub_Migration_Report.md` for download instructions.

4. **Config files need GPU_A values.** `machine.yaml` is empty and `storage.yaml` root needs to be set to `${DATA_ROOT}`.

---

*Research Agent v3 — GPU_A Migration Package*
