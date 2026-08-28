# START HERE — Research Agent v8.2.2

> **This is the only document you need to read first.**
> Version 8.2.2 | Python 3.12 | Conda: research_agent_v3
> Supports: Windows (CPU) and Linux (GPU) environments

---

## A. What Is This?

Research Agent v8.2.2 is a Skill + MCP + LLM + Human-in-the-loop driven automated research agent.
It automates a 15-module pipeline from literature retrieval to paper writing:

```
01 Literature Retrieval → 02 Source Acquisition → 02.5 Paper Asset Intelligence →
03 Literature Intelligence → 04 Research Landscape → 05 Innovation Reasoning →
06 Theory & Method → 07 Experiment Planning → 08 Synthetic Experiment →
09 Real Experiment → 10 Result Analysis → 11 Figure & Table →
12 Paper Writing → 13 Reference & Supplementary → 14 Reviewer Loop
```

Input: `configs/research_task.yaml` → Output: Complete paper files.

### v8.2.2 Key Features

- **Unified External Dependency Management**: `configs/external_dependency.yaml`
- **Centralized Fallback Policy**: `configs/dependency_policy.yaml` (modules must NOT decide fallback)
- **Skill Registry**: `infrastructure/skills/skill_registry.yaml` (with capability field)
- **MCP Registry**: `infrastructure/mcp/mcp_registry.yaml` (with installed/configured/tested status)
- **Literature Registry**: `data/literature/` (with research_task_id for cross-task deduplication)
- **Three Run Modes**: production / limited / development
- **First Time Setup Wizard**: Automated portability check with install order generation

---

## B. First Time Setup Wizard

### Step 1: Run Portability Check

```bash
conda activate research_agent_v3
python scripts/check_portability.py
```

The script automatically detects:
1. Python version (requires 3.12)
2. Conda environment (requires research_agent_v3)
3. Skill installation status
4. MCP installation status
5. LLM configuration
6. Model paths
7. GPU availability
8. Storage space

### Step 2: Review the Report

Open the generated `Migration_Check_Report.md`. The report lists:
- PASS: Ready components
- WARN: Optional components missing
- FAIL: Required components missing
- Suggested installation order (auto-generated)

### Step 3: Install Missing Components

Follow the installation order from the report:

```bash
# Example:
# 1. conda activate research_agent_v3
# 2. pip install -r requirements.txt
# 3. Install Skill: light-literature-search → c:/Users/<user>/.trae-cn/skills/
# 4. Install MCP: arxiv-mcp-server → uvx arxiv-mcp-server
# 5. Configure LLM: set DEEPSEEK_API_KEY environment variable
```

### Step 4: Re-run Check

```bash
python scripts/check_portability.py
```

Repeat until all required components are ready.

### Step 5: Start Pipeline

```bash
python -c "
from orchestrator.pipeline import PipelineOrchestrator
pipe = PipelineOrchestrator('configs/research_task.yaml')
result = pipe.start()
print(result)
"
```

---

## C. Quick Start (Experienced Users)

### C1. Prerequisites

- Python 3.12 (Conda environment: `research_agent_v3`)
- Internet connection (for literature retrieval and LLM API)
- Optional: NVIDIA GPU (for real experiments)

### C2. One-Command Check

```bash
conda activate research_agent_v3
python scripts/check_research_ready.py
```

This checks: Python env, LLM config, API connection, literature count, directory structure,
output writability, Skill installation, MCP installation, and portability.

### C3. Configure Your Research Task

Edit `configs/research_task.yaml`:

```yaml
task_id: "task_001"
domain: "computer_vision"
topic: "adversarial attacks on vision-language models"
keywords:
  - "adversarial attack VLM"
  - "vision-language model safety"
max_papers: 50
databases:
  - arxiv
  - semantic_scholar
  - openreview
```

### C4. Run the Pipeline

```bash
python -c "
from orchestrator.pipeline import PipelineOrchestrator
pipe = PipelineOrchestrator('configs/research_task.yaml')
result = pipe.start()
print(result)
"
```

---

## D. Run Modes

| Mode | Skills | MCP | LLM | Fallback | Mock |
|------|--------|-----|-----|----------|------|
| **Production** | Required skills must exist | Required MCP must work | Real LLM | Not allowed | Not allowed |
| **Limited** (default) | Optional | Optional | Template OK | Allowed | Not allowed |
| **Development** | Optional | Optional | Mock OK | All allowed | Allowed |

Change mode in `configs/external_dependency.yaml`:
```yaml
run_mode: limited  # production | limited | development
```

---

## E. Key Configuration Files

| File | Purpose |
|------|---------|
| `configs/external_dependency.yaml` | Unified external dependency entry point |
| `configs/dependency_policy.yaml` | Centralized fallback policy (modules must query, not decide) |
| `configs/environment.yaml` | Environment specification |
| `configs/research_task.yaml` | Research task configuration (edit this to start new research) |
| `configs/llm.yaml` | LLM provider configuration |
| `configs/model_registry.yaml` | VLM model registry |
| `infrastructure/skills/skill_registry.yaml` | Skill registry (original path, not migrated) |
| `infrastructure/mcp/mcp_registry.yaml` | MCP registry (original path, not migrated) |

---

## F. Literature Registry

The literature registry system enables cross-task deduplication:

| File | Format | Purpose |
|------|--------|---------|
| `data/literature/literature_registry.csv` | CSV | Full registry with 14 fields including research_task_id |
| `data/literature/literature_registry.xlsx` | Excel | Same as CSV, Excel format |
| `data/literature/literature_database.json` | JSON | Quick lookup database for dedup |
| `data/literature/literature_keyword_statistics.xlsx` | Excel | Keyword hit statistics |
| `data/literature/Literature_Download_Report.md` | Markdown | Download report per session |

---

## G. Documentation Index

| Document | Description |
|----------|-------------|
| [docs/Installation_Guide_CN.md](docs/Installation_Guide_CN.md) | Environment installation and configuration |
| [docs/Skill_Configuration_Guide_CN.md](docs/Skill_Configuration_Guide_CN.md) | Skill registration, capability, fallback management |
| [docs/MCP_Configuration_Guide_CN.md](docs/MCP_Configuration_Guide_CN.md) | MCP three-state status and installation |
| [docs/Literature_Registry_Guide_CN.md](docs/Literature_Registry_Guide_CN.md) | Literature registry usage and dedup mechanism |
| [docs/Module_Interface_Documentation_CN.md](docs/Module_Interface_Documentation_CN.md) | Module input/output documentation |
| [docs/Human_Intervention_Guide_CN.md](docs/Human_Intervention_Guide_CN.md) | Human-in-the-loop feedback |
| [docs/Troubleshooting_CN.md](docs/Troubleshooting_CN.md) | Common issues and solutions |
| [docs/LLM_Configuration_Guide_CN.md](docs/LLM_Configuration_Guide_CN.md) | LLM provider setup |
| [docs/Literature_Preparation_Guide_CN.md](docs/Literature_Preparation_Guide_CN.md) | Literature preparation guide |

---

## H. Architecture Overview

```
orchestrator/pipeline.py          ← Single entry point
├── configs/external_dependency.yaml   ← Unified dependency config
├── configs/dependency_policy.yaml     ← Centralized fallback policy
├── infrastructure/skills/             ← Skill runtime (original path)
├── infrastructure/mcp/                ← MCP manager (original path)
├── modules/01-14/                     ← 15 research modules
├── scripts/check_*.py                 ← Pre-pipeline checks
└── data/literature/                   ← Literature registry
```

**Fallback Flow**:
```
Module detects missing dependency
  → Module calls pipeline.get_fallback(module_id, dependency_type)
  → Pipeline queries dependency_policy.yaml
  → Returns action based on run_mode
  → Module executes fallback action
```

---

## I. Constraints

- Python 3.12 + Conda environment `research_agent_v3` (no new environment)
- Module interface (7-step lifecycle) is NOT modified
- Skill/MCP registries stay at original paths (not migrated)
- Fallback is centrally managed (modules must NOT decide on their own)

---

> For questions, see [docs/Troubleshooting_CN.md](docs/Troubleshooting_CN.md).
