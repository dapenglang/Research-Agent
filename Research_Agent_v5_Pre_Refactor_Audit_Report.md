# Research Agent v5 — Pre-Refactor Audit Report

> **Audit Date**: 2026-08-16  
> **Source**: `Research_Agent_v3_Server_Release_v4.zip` (332,508 bytes)  
> **Auditor**: TRAE AI Assistant  
> **Objective**: Full audit of v4 codebase before v5 unified refactor

---

## Executive Summary

The v4 release contains a well-structured 13-module framework with clean separation of concerns, but **cannot run end-to-end** due to 3 critical issues:

1. **Modules 01-07 import non-existent packages** (`literature.*`, `reasoning.*`) — these packages were developed in a legacy project structure and not included in the release
2. **`configs/providers.yaml` is wrapped in markdown code fences** — YAML parser silently falls back to mock defaults
3. **Pipeline has no module-skip mechanism** — Module 09 (real experiment) always executes and fails on machines without GPU

The v5 refactor must address these while unifying Windows/Linux support through configuration-driven experiment strategy.

---

## 1. Directory Structure Audit

### 1.1 Top-Level Structure

```
Research_Agent_v3/
├── adapters/              # Method backend interface + SAMRA adapter
├── cli/                   # CLI entry point (argparse)
├── configs/               # 5 YAML config files
├── core/                  # State machine, exceptions, provenance, validation, contracts
├── docs/                  # 14 documentation files (4 categories)
├── infrastructure/        # LLM, memory, models, storage, validation
├── modules/               # 13 modules (01-13), each with 6 files
├── orchestrator/          # Pipeline orchestrator
├── scripts/               # Setup scripts (.sh + .ps1)
├── tests/                 # 4 test files (90 tests)
├── START_HERE.md          # Entry point
├── VERSION.md             # v3.0.0, 2026-08-15
├── environment.yml        # Conda env spec
├── requirements.txt       # Python dependencies
├── __init__.py            # Package init, v3.0.0
└── Research_Task_Config_Fix_Report.md
```

### 1.2 Module Structure (each of 13 modules)

```
modules/XX_module_name/
├── interface.py          # Input/Output dataclasses + ABC Interface
├── implementation.py     # Concrete implementation
├── schema.py             # Validation schema
├── validator.py          # Custom validator
├── manifest.yaml         # Module metadata
└── __init__.py           # Package init
```

**Total file count**: 182 files  
**Total size**: 332 KB (compressed)

---

## 2. Module Completeness Audit (01-13)

| Module | Name | Interface | Implementation | Schema | Validator | Manifest | Can Run? |
|--------|------|-----------|----------------|--------|-----------|----------|----------|
| 01 | Literature Retrieval | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `literature.*` missing |
| 02 | Source Acquisition | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `literature.*` missing |
| 03 | Literature Intelligence | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `literature.*` missing |
| 04 | Research Landscape | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `reasoning.*` missing |
| 05 | Innovation Reasoning | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `reasoning.*` missing |
| 06 | Theory & Method | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `reasoning.*` missing |
| 07 | Experiment Planning | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `reasoning.*` missing |
| 08 | Synthetic Experiment | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `import adapters` fails |
| 09 | Real Experiment | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ `import adapters` fails |
| 10 | Result Analysis | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ No broken imports |
| 11 | Figure & Table | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ No broken imports |
| 12 | Paper Writing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ No broken imports |
| 13 | Reference & Supp. | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ No broken imports |

**Summary**: 7/13 modules have broken imports (01-07), 2/13 have adapter import issues (08-09), 4/13 are clean (10-13).

---

## 3. Broken Import Analysis

### 3.1 Missing Packages

| Import Path | Used By | Exists in Release? | Error Handling |
|-------------|---------|-------------------|----------------|
| `literature.downloader.paper_downloader` | Module 01, 02 | ❌ NO | Hard import — crashes |
| `literature.parser.pdf_parser` | Module 02 | ❌ NO | Hard import — crashes |
| `literature.parser.section_detector` | Module 02 | ❌ NO | Hard import — crashes |
| `literature.parser.markdown_formatter` | Module 02 | ❌ NO | Hard import — crashes |
| `literature.extractor.paper_extractor` | Module 03 | ❌ NO | Hard import — crashes |
| `literature.extractor.quality_checker` | Module 03 | ❌ NO | Hard import — crashes |
| `literature.database.paper_database` | Module 03 | ❌ NO | Hard import — crashes |
| `literature.pipeline.literature_pipeline` | Module 03 | ❌ NO | Hard import — crashes |
| `reasoning.gap_analyzer.*` | Module 04 | ❌ NO | Hard import — crashes |
| `reasoning.scientific_reasoner.*` | Modules 04, 05, 06 | ❌ NO | Hard import — crashes |
| `reasoning.hypothesis_generator.*` | Module 05 | ❌ NO | Hard import — crashes |
| `reasoning.method_designer.*` | Module 06 | ❌ NO | Hard import — crashes |
| `reasoning.experiment_designer.*` | Module 07 | ❌ NO | Hard import — crashes |
| `import adapters` (bare) | Modules 08, 09 | ❌ Not top-level | Hard import — crashes |
| `research_agent.experimental.*` | SAMRA adapter | ❌ NO | try/except — returns error result |
| `research_agent.samra.*` | SAMRA adapter | ❌ NO | try/except — returns error result |

### 3.2 Import Pattern Inconsistency

| Modules | Import Style | Issue |
|---------|-------------|-------|
| 01-03 | Dynamic `importlib.util` + bare `from interface import` | Inconsistent with package structure |
| 04-07 | Relative `from .interface import` | Requires package context |
| 08-13 | Bare `from interface import` | Requires module dir on sys.path |

**v5 Recommendation**: Unify all modules to use absolute imports from the package root.

---

## 4. CLI Entry Point Audit

### 4.1 CLI Structure

**File**: `cli/cli.py`  
**Parser**: argparse with 4 subcommands

| Command | Description | Implementation |
|---------|-------------|----------------|
| `start` | Start new pipeline run | `orchestrator.run(task_config_path)` |
| `resume` | Resume from last checkpoint | `orchestrator.resume()` |
| `rerun` | Re-execute from specific module | `orchestrator.rerun(module_id)` |
| `status` | Show pipeline state | `orchestrator.get_status()` |

### 4.2 Issues

- **No `--skip` flag**: Cannot skip modules via CLI
- **No `--scheme` flag**: Cannot select experiment scheme (A/B/C)
- **No `--detect` flag**: Cannot trigger environment detection
- **Windows path handling**: ✅ Uses `Path(__file__).resolve()` — correct
- **Exit code**: `status` command always returns 0 even if pipeline failed

---

## 5. Pipeline Orchestrator Audit

### 5.1 Module Execution Flow

```
_load_modules() → _run_pipeline() → _execute_module() → _build_input()
```

**Module sequence**: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13

### 5.2 Failure Handling

| Failure Point | Action | State Effect |
|---------------|--------|--------------|
| Module load exception | `state.fail_module()`, return FAIL | Module marked failed |
| Input validation fail | `state.fail_module()`, return FAIL | Module marked failed |
| Execute exception | `state.fail_module()`, return FAIL | Module marked failed |
| Output validation fail | `state.fail_module()`, return FAIL | Module marked failed |
| Quality hard req fail | Status = WARNING, **module still marked completed** | **BUG: resume skips it** |

### 5.3 Critical Issues

1. **No skip mechanism**: Pipeline always executes all 13 modules sequentially. Cannot skip Module 09 when no GPU.

2. **Quality WARNING bug**: When `quality_assessment()` returns failed hard requirements:
   - Status set to `"WARNING"`
   - `state.complete_module()` still called (line 335)
   - Pipeline stops (WARNING != PASS)
   - On resume, module is in `completed_modules` → **skipped without re-check**

3. **Orchestrator-contract type mismatch**:
   - Contract declares `execute()` returns `Dict[str, Any]`
   - Orchestrator accesses `output.manifest` and `output.output_files` as attributes
   - Contract declares `quality_assessment()` returns `tuple[ModuleStatus, float]`
   - Orchestrator treats it as `dict` with `quality.get("hard_requirements", {})`

4. **Truthiness check bug**: `if not instance.validate_input(input_data)` — `ModuleStatus` is `str` enum, all values are truthy. Failed validation never caught.

5. **No automatic retry**: `ResearchState` has `max_retries=3` but orchestrator never calls `can_retry()`.

6. **Missing encoding**: `open(decision_path, "r")` without `encoding="utf-8"` — Windows cp1252 may fail on non-ASCII.

### 5.4 Data Flow Between Modules

Three mechanisms:
1. **`_module_outputs` dict**: Full output objects stored in memory
2. **`_collect_input_files()`**: All upstream `output_files` merged into flat dict
3. **`_get_upstream_fields()`**: Specific upstream outputs mapped to named Input fields

Module-specific upstream mapping:
- Module 10: receives `upstream_module_07`, `upstream_module_08`, `upstream_module_09`
- Module 11: receives `upstream_module_06/07/08/09/external`
- Module 12: receives `upstream_module_all` (all manifests)
- Module 13: receives `upstream_module_01`, `upstream_module_12`

---

## 6. Configuration Audit

### 6.1 Config File Validity

| File | Valid YAML? | Critical Issues |
|------|-------------|-----------------|
| `machine.yaml` | ✅ | Hardcoded to specific machine (Windows 11, RTX A500 4GB) |
| `providers.yaml` | ❌ **BROKEN** | Wrapped in markdown code fences (``` ```yaml ... ``` ```) |
| `model_registry.yaml` | ✅ | All models require 16-18GB VRAM, no 4GB-compatible option |
| `storage.yaml` | ✅ | `root: ""` — user must set manually |
| `research_task_template.yaml` | ✅ | Well-structured, no `experiment.real.enabled` toggle |

### 6.2 providers.yaml Bug Detail

```yaml
# File starts with:
```yaml          ← INVALID YAML
providers:
  llm:
    ...
```              ← INVALID YAML
```

**Impact**: `yaml.safe_load()` returns a string, not a dict. `ConfigLoader` silently skips it, falling back to DEFAULTS with `type: "mock"`. All LLM configuration is ignored.

### 6.3 ConfigLoader Schema Mismatch

| ConfigLoader expects | Actual config has | Impact |
|---------------------|------------------|--------|
| `storage.paths.DATA_ROOT` | `storage.root` + `storage.subdirs` | Variable resolution uses wrong defaults |
| `providers.default.type` | `providers.llm.default` (string) | Provider validation never triggers |
| `providers.default.api_key` | `providers.llm.openai.api_key_env` | API key check never triggers |
| `auto_download.enabled` (dict) | `auto_download: true` (bool) | AttributeError on validation |

### 6.4 Experiment Strategy Configurability

**Current state**: No top-level `experiment.strategy` toggle. Both Module 08 and 09 always execute.

```yaml
# What exists:
experiment:
  synthetic:
    num_samples: 1000
    seed: 42
  real:
    checkpoint_dir: "checkpoints"
    resume_from_checkpoint: false
    seed: 42

# What's missing:
experiment:
  strategy: "synthetic_only"  # or "real_only" or "both"
  real:
    enabled: false            # No enable/disable toggle
```

### 6.5 GPU Configuration

```yaml
# Current (hardcoded):
gpu:
  available: true
  device: "NVIDIA RTX A500 Laptop GPU"
  vram_gb: 4
  cuda_version: "12.1"

# v5 needs:
gpu:
  available: false            # Auto-detected
  device: ""                  # Auto-detected
  vram_gb: 0                  # Auto-detected
  cuda_version: ""            # Auto-detected
```

---

## 7. State Machine Audit

### 7.1 States (14 total)

```
INIT → LOADING_CONFIG → DEPENDENCY_CHECK → MODULE_EXECUTING → VALIDATION_GATE
→ DECISION_ROUTING → CHECKPOINT → COMPLETED / FAILED / PAUSED_HUMAN_REVIEW
```

Plus experiment states: `EXPERIMENT_RUNNING`, `EXPERIMENT_INTERRUPTED`, `EXPERIMENT_RESUMING`

### 7.2 Module Status Enum

```python
class ModuleStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCKED = "blocked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    SKIPPED = "skipped"           # ← Defined but NEVER used
```

### 7.3 Issues

- **`SKIPPED` status defined but never used** — no `skip_module()` method in `ResearchState`
- **`ModuleStateRecord.status` uses plain strings** ("pending", "running", "completed", "failed") — never set to "skipped"
- **No module-level skip** — only pipeline-level pause (`PAUSED_HUMAN_REVIEW`)
- **Unused imports**: `os` in `state_machine.py`, `yaml` in `checkpoint.py`

---

## 8. Infrastructure Audit

### 8.1 LLM Provider System

**Files**: `infrastructure/llm/llm_provider.py`, `prompt_manager.py`

| Provider | Class | Status |
|----------|-------|--------|
| OpenAI | `OpenAIProvider` | ✅ Lazy import of `openai` package |
| Local | `LocalLLMProvider` | ✅ HTTP calls via `requests` (lazy) |
| Mock | `MockProvider` | ✅ Keyword-matching, no external deps |

**Issues**:
- Provider type `"none"` accepted by validator but not by factory
- `validate_usage()` enforces mock prohibition for `paper_generation` — good

### 8.2 Model Hub

**File**: `infrastructure/models/model_hub.py`

- Load protocol: local_path → auto_download → FAIL (never mock)
- Heavy dependencies (`torch`, `transformers`, `huggingface_hub`) all lazily imported
- `torch_dtype="auto"` may be version-dependent
- `model_validator.py` line 186: `IndexError` risk if `architectures` is empty list

### 8.3 Storage System

**Files**: `infrastructure/storage/path_resolver.py`, `storage_manager.py`

- `PathResolver`: Recursive `${VARIABLE}` substitution, 8 variables supported
- `StorageManager`: Category-based path resolution, disk-space checking
- **Inconsistency**: `PathResolver._substitute` raises `KeyError` for unresolved vars, but `ConfigLoader._substitute` leaves them in place
- **Documentation bug**: `get_path()` docstring says "auto-created" but doesn't create dirs

### 8.4 Memory System

**Files**: `infrastructure/memory/memory_store.py`, `memory_retriever.py`, `usage_logger.py`

- Three-layer JSON storage (universal, domains, projects)
- Relevance scoring: 6 components (keyword 25%, semantic 25%, domain 20%, module 15%, verification 10%, time 5%)
- **Performance issue**: `rglob("*.json")` on every query — no indexing
- **No file locking**: concurrent writes could corrupt

### 8.5 Config Loader

**File**: `infrastructure/validation/config_loader.py`

- Loads 5 config files, merges with DEFAULTS
- **Not used by orchestrator** — orchestrator directly loads `research_task.yaml` via `yaml.safe_load()`
- Schema mismatch with actual config files (see section 6.3)

---

## 9. Adapter System Audit

### 9.1 Method Backend Interface

**File**: `adapters/method_backend_interface.py`

| Component | Purpose |
|-----------|---------|
| `MethodSpec` | Method specification dataclass |
| `ExperimentResult` | Experiment output dataclass (metrics, raw_data, data_origin, seed) |
| `MethodBackend` (ABC) | Abstract backend: `load_spec()`, `run_synthetic_experiment()`, `run_real_experiment()` |
| `BackendRegistry` | Registry singleton with `register()`, `get()`, `list_available()` |

**Dependencies**: `numpy` only — no GPU required

### 9.2 SAMRA Adapter

**File**: `adapters/samra_adapter.py`

| Method | Imports | Status |
|--------|---------|--------|
| `run_synthetic_experiment()` | `research_agent.experimental.*` (3 modules) | ❌ ImportError → empty metrics → FAIL |
| `run_real_experiment()` | `research_agent.samra.*` (4 modules) | ❌ ImportError → empty metrics → FAIL |

**Impact**: Both synthetic and real experiments fail because the SAMRA backend code was not included in the release.

---

## 10. Test Suite Audit

### 10.1 Test Inventory

| File | Framework | Tests | Coverage | GPU Required |
|------|-----------|-------|----------|--------------|
| `test_v3_literature.py` | unittest | 30 | Modules 01-03 lifecycle + chain | ❌ No |
| `test_v3_reasoning.py` | unittest | 30 | Modules 04-07 + LLM compat | ❌ No |
| `test_research_task_config.py` | pytest | 28 | Config field reading + validation | ❌ No |
| `test_phase_d_e2e.py` | script | 2 | Full 13-module E2E | ❌ No |
| **Total** | | **90** | | |

### 10.2 Test Issues

- Tests mock `PaperDownloader`, `PDFParser` — but these classes don't exist (imported from non-existent `literature.*`)
- E2E test creates mock data for all modules but may fail on import
- No tests for Modules 08-13 individually
- No GPU/CUDA tests
- No platform-specific tests (Windows/Linux)

---

## 11. Documentation Audit

### 11.1 Documentation Inventory

| # | Document | Location | Status |
|---|----------|----------|--------|
| 1 | START_HERE.md | Root | ✅ Current |
| 2 | VERSION.md | Root | ✅ v3.0.0 |
| 3 | Windows Deployment Guide | `docs/01_Deployment/` | ✅ Comprehensive |
| 4 | Module Usage Guide | `docs/02_Usage/` | ✅ All 13 modules |
| 5 | New Research Task Guide | `docs/02_Usage/` | ✅ Current |
| 6 | Configuration Guide | `docs/03_Configuration/` | ✅ All 5 configs |
| 7 | LLM Provider Guide | `docs/03_Configuration/` | ✅ Current |
| 8 | Model Hub Guide | `docs/03_Configuration/` | ✅ Current |
| 9 | Troubleshooting Guide | `docs/04_Troubleshooting/` | ✅ 14 issues |
| 10 | GPU_A First Run Checklist | `docs/99_Archive/` | ⚠️ Archived, Python 3.10 |
| 11 | README_GPU_A | `docs/99_Archive/` | ⚠️ Archived, Python 3.10 |

### 11.2 Documentation Gaps

1. **No Linux deployment guide** — only Windows guide exists
2. **Archived docs reference Python 3.10** — should be 3.12
3. **Config Guide shows providers.yaml WITHOUT fences** — docs describe intended state, not actual broken file
4. **No architecture/API documentation** — no internal data flow diagram
5. **No CI/CD or testing strategy doc**
6. **Mixed language** — `Research_Task_Config_Fix_Report.md` is in Chinese, all others English

---

## 12. Environment Audit

### 12.1 Conda Environment

| Item | Value | Status |
|------|-------|--------|
| Environment name | `research_agent_v3` | ✅ Exists |
| Python version | 3.12.13 | ✅ Matches requirement |
| PyTorch | 2.5.1+cu121 | ✅ Installed (CUDA 12.1) |
| numpy | 2.5.2 | ✅ Installed |
| Pillow | 12.3.0 | ✅ Installed |
| scipy | — | ❌ Missing |
| pandas | — | ❌ Missing |
| matplotlib | — | ❌ Missing |
| openai | — | ❌ Missing |
| pyyaml | — | ❌ Missing |
| pytest | — | ❌ Missing |
| python-docx | — | ❌ Missing |
| beautifulsoup4 | — | ❌ Missing |
| lxml | — | ❌ Missing |
| scikit-learn | — | ❌ Missing |
| tqdm | — | ❌ Missing |
| requests | — | ❌ Missing |
| openpyxl | — | ❌ Missing |
| markdownify | — | ❌ Missing |

**Action**: Installing missing packages via `pip install` (in progress).

### 12.2 GPU Status

| Item | Value |
|------|-------|
| GPU available | ❌ No (current machine: Windows, no NVIDIA GPU) |
| CUDA available | ❌ No |
| Experiment capability | Synthetic only (Scheme A) |

---

## 13. Critical Issues Summary

### 13.1 Blocking Issues (Must Fix for v5)

| # | Severity | Component | Issue | v5 Fix |
|---|----------|-----------|-------|--------|
| 1 | **CRITICAL** | `configs/providers.yaml` | Markdown code fences break YAML parsing | Remove fences |
| 2 | **CRITICAL** | Modules 01-07 | Import non-existent `literature.*` and `reasoning.*` packages | Inline implementations or create stub packages |
| 3 | **CRITICAL** | Modules 08-09 | `import adapters` bare import fails | Use absolute import `from Research_Agent.adapters import ...` |
| 4 | **CRITICAL** | `adapters/samra_adapter.py` | `research_agent.experimental.*` and `research_agent.samra.*` don't exist | Inline synthetic experiment implementation |
| 5 | **HIGH** | `orchestrator/pipeline.py` | No module-skip mechanism | Add `skip_modules` config + SKIP status |
| 6 | **HIGH** | `orchestrator/pipeline.py` | Quality WARNING marks module as completed | Don't call `complete_module()` on WARNING |
| 7 | **HIGH** | `orchestrator/pipeline.py` | Truthiness check bug on ModuleStatus | Check `== ModuleStatus.FAIL` instead of `not` |
| 8 | **HIGH** | `core/contracts/module_contract.py` | Contract return types don't match orchestrator usage | Align contract with actual implementation |
| 9 | **HIGH** | `infrastructure/validation/config_loader.py` | Schema mismatch with actual configs | Update DEFAULTS and validation |
| 10 | **MEDIUM** | `configs/machine.yaml` | Hardcoded to specific machine | Auto-generate from environment detection |
| 11 | **MEDIUM** | `configs/model_registry.yaml` | All models require 16-18GB VRAM | Add 4GB-compatible models or auto-filter |
| 12 | **MEDIUM** | `core/state/state_machine.py` | `SKIPPED` status defined but never used | Add `skip_module()` method |
| 13 | **MEDIUM** | `core/provenance/provenance.py` | `LLM_GENERATED` not in `DataOrigin` enum | Add to enum |
| 14 | **LOW** | `orchestrator/pipeline.py` | Missing `encoding="utf-8"` on file read | Add encoding |
| 15 | **LOW** | Various | Unused imports (`os`, `yaml`) | Remove |

### 13.2 Architecture Issues for v5

1. **No environment detection** — `machine.yaml` is manually configured
2. **No experiment strategy toggle** — can't select Scheme A/B/C via config
3. **No Linux deployment guide** — only Windows documented
4. **Inconsistent import patterns** — 3 different styles across 13 modules
5. **ConfigLoader not used by orchestrator** — two separate config loading paths
6. **No automatic retry** — `max_retries` defined but never used

---

## 14. v5 Refactor Recommendations

### 14.1 Priority Order

1. **Fix broken imports** (Modules 01-09) — inline or stub legacy packages
2. **Fix providers.yaml** — remove markdown fences
3. **Add module-skip mechanism** — `SKIPPED` status + `skip_modules` config
4. **Add environment detection** — `scripts/environment_detector.py`
5. **Add config auto-generation** — `machine.yaml` from detected environment
6. **Add experiment strategy config** — `experiment.strategy: synthetic_only|real_only|both`
7. **Fix orchestrator bugs** — truthiness, quality WARNING, encoding
8. **Unify import patterns** — all absolute imports from package root
9. **Align ConfigLoader with actual configs** — update DEFAULTS and validation
10. **Add Linux deployment guide** — document both platforms

### 14.2 v5 Target Structure

```
Research_Agent_Release_v5/
├── Research_Agent/
│   ├── __init__.py
│   ├── adapters/
│   ├── cli/
│   ├── core/
│   ├── infrastructure/
│   ├── modules/
│   │   ├── 01_literature_retrieval/
│   │   ├── ...
│   │   └── 13_reference_supplementary/
│   └── orchestrator/
├── configs/
│   ├── machine.yaml           # Auto-generated
│   ├── providers.yaml         # Fixed
│   ├── model_registry.yaml
│   ├── storage.yaml
│   └── research_task_template.yaml
├── tasks/
├── models/
├── outputs/
├── docs/
├── scripts/
│   ├── environment_detector.py    # NEW
│   ├── generate_machine_config.py # NEW
│   ├── setup_environment.sh
│   └── setup_environment.ps1
├── tests/
└── START_HERE_CN.md
```

### 14.3 Configuration-Driven Experiment Strategy

```yaml
# research_task_template.yaml (v5)
experiment:
  strategy: "synthetic_only"    # synthetic_only | real_only | both
  synthetic:
    enabled: true
    num_samples: 1000
    seed: 42
  real:
    enabled: false              # Auto-set based on strategy + GPU
    checkpoint_dir: "checkpoints"
    resume_from_checkpoint: false
    seed: 42
```

Pipeline behavior:
- `synthetic_only`: Execute Module 08, skip Module 09 (status=SKIPPED)
- `real_only`: Skip Module 08 (status=SKIPPED), execute Module 09
- `both`: Execute Module 08 then Module 09 (current behavior)

---

## 15. Conclusion

The v4 release provides a solid architectural foundation with clean separation of concerns, but is **not runnable** due to missing backend packages and configuration bugs. The v5 refactor should:

1. **Make it runnable** — fix all broken imports and config issues
2. **Make it unified** — single codebase for Windows/Linux, config-driven experiment strategy
3. **Make it automatic** — environment detection and config auto-generation
4. **Make it robust** — fix orchestrator bugs, add skip mechanism, align contracts

---

*End of Audit Report*
