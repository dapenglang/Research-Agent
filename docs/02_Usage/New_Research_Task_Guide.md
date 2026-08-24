# New Research Task Guide — Research Agent v3

**Date:** 2026-08-15

---

## Overview

When you want to start a new research task, you do **NOT** modify code. You only modify a task configuration file: `research_task.yaml`.

---

## 1. Where Is the Template?

The complete research task template is at:
```
configs/research_task_template.yaml
```

Copy it to your project root:
```powershell
copy configs\research_task_template.yaml my_research_task.yaml
```

**Note:** `tests/e2e_test_data/research_task.yaml` is a minimal E2E test config that lacks research content fields. Do NOT use it as a template for real research. Always use `configs/research_task_template.yaml`.

---

## 2. Template Structure

```yaml
# ---- Task Identity (REQUIRED) ----
task_id: "my_research_001"
title: "Your Research Title"

# ---- Research Content (REQUIRED — drives Modules 01-07) ----
research:
  domain: "computer_vision"           # e.g. computer_vision, nlp, reinforcement_learning
  topic: "Adversarial Robustness of VLMs"  # Specific topic
  keywords:                           # Search keywords for literature retrieval
    - "adversarial attack"
    - "vision-language model"
    - "robustness"
  research_question: "How do adversarial patches affect VLM reasoning?"
  target: "LLaVA-1.5-7B"             # Target model/method/system

# ---- Literature Acquisition (OPTIONAL — drives Modules 01-02) ----
literature:
  candidate_target: []               # Paper IDs to consider (empty = auto-search)
  core_target: []                    # Paper IDs for deep analysis (empty = auto-select)
  deep_analysis_target: []
  arxiv:
    download_pdf: true               # Download PDF files from arXiv
    download_source: false           # Download LaTeX source from arXiv
    prefer_latex_analysis: true       # Prefer LaTeX over PDF for parsing

# ---- LLM Configuration (REQUIRED) ----
llm:
  type: "openai"                     # "openai", "local", or "mock" (mock for testing ONLY)

# ---- Experiment Configuration (drives Modules 07-09) ----
experiment:
  method: "samra"
  synthetic:
    num_samples: 100
    seed: 42
  real:
    checkpoint_dir: "checkpoints"
    resume_from_checkpoint: false
    seed: 42

# ---- Analysis Configuration (Module 10) ----
analysis:
  output_dir: "output/analysis"
  significance_level: 0.05

# ---- Output Directories (Modules 11-13) ----
output:
  figure_table_dir: "output/figures_tables"
  paper_dir: "output/paper"
  reference_dir: "output/references"

# ---- Paper Configuration (Modules 12-13) ----
paper:
  min_references: 5
```

---

## 3. Field Reference

### 3.1 Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `task_id` | str | Unique identifier for this research task | `"adversarial_vlm_001"` |
| `title` | str | Human-readable title | `"Adversarial Attacks on VLMs"` |
| `research.domain` | str | Research domain | `"computer_vision"`, `"nlp"` |
| `research.keywords` | List[str] | Search keywords for literature retrieval | `["adversarial", "VLM"]` |
| `research.research_question` | str | Core research question | `"How do patches affect VLMs?"` |
| `llm.type` | str | LLM provider type | `"openai"`, `"local"`, `"mock"` |

### 3.1b Research Content Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `research.domain` | str | Yes | Research domain (e.g. `computer_vision`, `nlp`, `rl`) |
| `research.topic` | str | No | Specific research topic |
| `research.keywords` | List[str] | Yes | Search keywords for literature retrieval |
| `research.research_question` | str | Yes | Core research question driving the pipeline |
| `research.target` | str | No | Target model/method/system to study |

### 3.1c Literature Acquisition Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `literature.candidate_target` | List[str] | `[]` | Paper IDs to consider (empty = auto-search) |
| `literature.core_target` | List[str] | `[]` | Paper IDs for deep analysis (empty = auto-select) |
| `literature.deep_analysis_target` | List[str] | `[]` | Paper IDs for deep analysis (empty = auto-select) |
| `literature.arxiv.download_pdf` | bool | `true` | Download PDF files from arXiv |
| `literature.arxiv.download_source` | bool | `false` | Download LaTeX source from arXiv |
| `literature.arxiv.prefer_latex_analysis` | bool | `true` | Prefer LaTeX source over PDF for parsing |

### 3.2 Experiment Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `experiment.method` | str | Method backend name | `"samra"` |
| `experiment.synthetic.num_samples` | int | Synthetic experiment sample count | 100 |
| `experiment.synthetic.seed` | int | Synthetic experiment seed | 42 |
| `experiment.real.checkpoint_dir` | str | Real experiment checkpoint directory | `"checkpoints"` |
| `experiment.real.resume_from_checkpoint` | bool | Resume from last checkpoint | false |
| `experiment.real.seed` | int | Real experiment seed | 42 |

### 3.3 Analysis Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `analysis.output_dir` | str | Analysis output directory | `"output/analysis"` |
| `analysis.significance_level` | float | Alpha for statistical tests | 0.05 |

### 3.4 Output Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `output.figure_table_dir` | str | Figure/table output directory | `"output/figures_tables"` |
| `output.paper_dir` | str | Paper output directory | `"output/paper"` |
| `output.reference_dir` | str | Reference output directory | `"output/references"` |

### 3.5 Paper Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `paper.min_references` | int | Minimum references in final paper | 5 |

---

## 4. Research Context — NOT Auto-Generated

The following fields are **required** in `research_task.yaml` and are **NOT** auto-generated:

- `research.domain` — Must be set by the user
- `research.keywords` — Must be set by the user
- `research.research_question` — Must be set by the user

The following fields have defaults and are optional:

- `max_papers` — Defaults to 50 (Module 01)
- `databases` — Defaults to `["arxiv", "semantic_scholar", "openreview"]` (Module 01)

---

## 5. Minimal Example

```yaml
# my_research_task.yaml — Minimal config for a new research task
task_id: "vlm_robustness_001"
title: "Adversarial Robustness of Vision-Language Models"

research:
  domain: "computer_vision"
  keywords: ["adversarial", "VLM", "robustness"]
  research_question: "How do adversarial patches affect VLM reasoning?"

llm:
  type: "openai"          # Use real LLM for production (NOT mock)

experiment:
  method: "samra"
  synthetic:
    num_samples: 100
    seed: 42
  real:
    checkpoint_dir: "checkpoints"
    resume_from_checkpoint: false
    seed: 42

analysis:
  output_dir: "output/analysis"
  significance_level: 0.05

output:
  figure_table_dir: "output/figures_tables"
  paper_dir: "output/paper"
  reference_dir: "output/references"

paper:
  min_references: 5
```

---

## 6. How to Start

```powershell
# 1. Create your task config
copy configs\research_task_template.yaml my_research_task.yaml

# 2. Edit my_research_task.yaml (set task_id, title, research.* fields, llm.type)

# 3. Start the pipeline
python -m Research_Agent_v3.cli.cli start --task my_research_task.yaml

# 4. Monitor progress
python -m Research_Agent_v3.cli.cli status --task my_research_task.yaml

# 5. If interrupted, resume
python -m Research_Agent_v3.cli.cli resume --task my_research_task.yaml
```

---

## 7. Changing Research Domain

To switch from one research area to another:

1. Copy the template to a new file (e.g. `nlp_fairness_task.yaml`)
2. Change `task_id` to a new unique ID
3. Change `title` to your new research topic
4. Optionally set `research.target`, `literature.*` fields
5. Start the pipeline with the new task file

The system will automatically:
- Retrieve relevant literature for the new domain
- Analyze and identify gaps
- Generate innovation candidates
- Design method and experiments
- Run experiments and generate paper

---

## 8. Changing Models or Datasets

To use different VLM models or datasets:

1. Edit `configs/model_registry.yaml` — Add/remove models, set local paths
2. Edit `configs/storage.yaml` — Ensure data root points to your data
3. Edit `configs/machine.yaml` — Update GPU info if hardware changed
4. Edit `configs/providers.yaml` — Set LLM provider if changed

See: [Configuration Guide](../03_Configuration/Configuration_Guide.md)
