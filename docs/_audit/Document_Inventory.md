# Document Inventory — Research Agent v3

**Audit Date:** 2026-08-15
**Auditor:** Release Consolidation Process
**Project Root:** Research_Agent_v3/

## Legend

| Status | Meaning |
|--------|---------|
| CURRENT | Active document, part of final release |
| ARCHIVED | Historical document, moved to docs/99_Archive/ |
| SUPERSEDED | Replaced by a new document (see "Replaced By") |
| DUPLICATE | Duplicate content, keep one copy |

## Source Code & Configuration

| File | Path | Type | Purpose | Status | In Release? |
|------|------|------|---------|--------|-------------|
| `__init__.py` | `Research_Agent_v3/__init__.py` | Python | Package init, version 3.0.0 | CURRENT | Yes |
| `cli.py` | `Research_Agent_v3/cli/cli.py` | Python | CLI entry (start/resume/rerun/status) | CURRENT | Yes |
| `pipeline.py` | `Research_Agent_v3/orchestrator/pipeline.py` | Python | PipelineOrchestrator, module dispatch | CURRENT | Yes |
| `environment.yml` | `Research_Agent_v3/environment.yml` | YAML | Conda env, Python 3.12 | CURRENT | Yes |
| `requirements.txt` | `Research_Agent_v3/requirements.txt` | TXT | pip dependencies | CURRENT | Yes |
| `machine.yaml` | `Research_Agent_v3/configs/machine.yaml` | YAML | Machine config, Python 3.12 | CURRENT | Yes |
| `storage.yaml` | `Research_Agent_v3/configs/storage.yaml` | YAML | Storage directory config | CURRENT | Yes |
| `providers.yaml` | `Research_Agent_v3/configs/providers.yaml` | YAML | LLM provider config | CURRENT | Yes |
| `model_registry.yaml` | `Research_Agent_v3/configs/model_registry.yaml` | YAML | VLM model registry | CURRENT | Yes |
| `setup_environment.sh` | `Research_Agent_v3/scripts/setup_environment.sh` | Bash | Linux env setup, Python 3.12 | CURRENT | Yes |
| `setup_environment_windows.ps1` | `Research_Agent_v3/scripts/setup_environment_windows.ps1` | PowerShell | Windows env setup, Python 3.12 | CURRENT | Yes |

## Modules (01-13)

| Module | Path | Status | In Release? |
|--------|------|--------|-------------|
| 01 Literature Retrieval | `modules/01_literature_retrieval/` | CURRENT | Yes |
| 02 Source Acquisition | `modules/02_source_acquisition/` | CURRENT | Yes |
| 03 Literature Intelligence | `modules/03_literature_intelligence/` | CURRENT | Yes |
| 04 Research Landscape | `modules/04_research_landscape/` | CURRENT | Yes |
| 05 Innovation Reasoning | `modules/05_innovation_reasoning/` | CURRENT | Yes |
| 06 Theory & Method | `modules/06_theory_method/` | CURRENT | Yes |
| 07 Experiment Planning | `modules/07_experiment_planning/` | CURRENT | Yes |
| 08 Synthetic Experiment Engine | `modules/08_synthetic_experiment_engine/` | CURRENT | Yes |
| 09 Real Experiment Engine | `modules/09_real_experiment_engine/` | CURRENT | Yes |
| 10 Result Analysis | `modules/10_result_analysis/` | CURRENT | Yes |
| 11 Figure & Table | `modules/11_figure_table/` | CURRENT | Yes |
| 12 Paper Writing | `modules/12_paper_writing/` | CURRENT | Yes |
| 13 Reference & Supplementary | `modules/13_reference_supplementary/` | CURRENT | Yes |

Each module contains: `implementation.py`, `interface.py`, `schema.py`, `validator.py`, `manifest.yaml`.

## Infrastructure

| File | Path | Type | Purpose | Status | In Release? |
|------|------|------|---------|--------|-------------|
| `llm_provider.py` | `infrastructure/llm/llm_provider.py` | Python | LLM provider (OpenAI/Local/Mock) | CURRENT | Yes |
| `prompt_manager.py` | `infrastructure/llm/prompt_manager.py` | Python | LLM prompt management | CURRENT | Yes |
| `model_hub.py` | `infrastructure/models/model_hub.py` | Python | Model loading & validation | CURRENT | Yes |
| `model_validator.py` | `infrastructure/models/model_validator.py` | Python | Model integrity validation | CURRENT | Yes |
| `storage_manager.py` | `infrastructure/storage/storage_manager.py` | Python | Storage path management | CURRENT | Yes |
| `path_resolver.py` | `infrastructure/storage/path_resolver.py` | Python | `${DATA_ROOT}` path resolution | CURRENT | Yes |
| `memory_store.py` | `infrastructure/memory/memory_store.py` | Python | Memory store | CURRENT | Yes |
| `memory_retriever.py` | `infrastructure/memory/memory_retriever.py` | Python | Memory retrieval & scoring | CURRENT | Yes |
| `config_loader.py` | `infrastructure/validation/config_loader.py` | Python | YAML config loading | CURRENT | Yes |

## Core

| File | Path | Type | Purpose | Status | In Release? |
|------|------|------|---------|--------|-------------|
| `state_machine.py` | `core/state/state_machine.py` | Python | Research state (incl. EXPERIMENT_RUNNING/INTERRUPTED/RESUMING) | CURRENT | Yes |
| `checkpoint.py` | `core/state/checkpoint.py` | Python | Checkpoint management | CURRENT | Yes |
| `exceptions.py` | `core/exceptions/exceptions.py` | Python | Custom exceptions | CURRENT | Yes |
| `provenance.py` | `core/provenance/provenance.py` | Python | Provenance tracking | CURRENT | Yes |
| `module_contract.py` | `core/contracts/module_contract.py` | Python | Module contract base | CURRENT | Yes |
| `data_contract.py` | `core/contracts/data_contract.py` | Python | Data contract base | CURRENT | Yes |
| `validator.py` | `core/validation/validator.py` | Python | Validation utilities | CURRENT | Yes |

## Adapters

| File | Path | Type | Purpose | Status | In Release? |
|------|------|------|---------|--------|-------------|
| `samra_adapter.py` | `adapters/samra_adapter.py` | Python | SAMRA method backend adapter | CURRENT | Yes |
| `method_backend_interface.py` | `adapters/method_backend_interface.py` | Python | Backend interface & registry | CURRENT | Yes |

## Tests

| File | Path | Type | Purpose | Status | In Release? |
|------|------|------|---------|--------|-------------|
| `test_v3_literature.py` | `tests/test_v3_literature.py` | Python | Literature pipeline tests (38 pass) | CURRENT | Yes |
| `test_v3_reasoning.py` | `tests/test_v3_reasoning.py` | Python | Reasoning pipeline tests (49 pass) | CURRENT | Yes |
| `test_phase_d_e2e.py` | `tests/test_phase_d_e2e.py` | Python | E2E test for modules 10-13 | CURRENT | Yes |
| `research_task.yaml` | `tests/e2e_test_data/research_task.yaml` | YAML | E2E test task config | CURRENT | Yes |

## Documentation — Old (To Be Archived)

| File | Path | Status | Replaced By |
|------|------|--------|-------------|
| `GPU_A_First_Run_Checklist.md` | `docs/GPU_A_First_Run_Checklist.md` | ARCHIVED | `docs/01_Deployment/Windows_Deployment_Guide.md` |
| `README_GPU_A.md` | `docs/README_GPU_A.md` | ARCHIVED | `docs/01_Deployment/Windows_Deployment_Guide.md` |

## Documentation — New (Final Release)

| File | Path | Purpose |
|------|------|---------|
| `START_HERE.md` | `START_HERE.md` | Unique entry point |
| `VERSION.md` | `VERSION.md` | Version info |
| `Windows_Deployment_Guide.md` | `docs/01_Deployment/Windows_Deployment_Guide.md` | Windows deployment guide |
| `Module_Usage_Guide.md` | `docs/02_Usage/Module_Usage_Guide.md` | Module 01-13 usage |
| `New_Research_Task_Guide.md` | `docs/02_Usage/New_Research_Task_Guide.md` | New task setup |
| `Configuration_Guide.md` | `docs/03_Configuration/Configuration_Guide.md` | All config files |
| `Model_Hub_Guide.md` | `docs/03_Configuration/Model_Hub_Guide.md` | Model management |
| `LLM_Provider_Guide.md` | `docs/03_Configuration/LLM_Provider_Guide.md` | LLM provider config |
| `Troubleshooting_Guide.md` | `docs/04_Troubleshooting/Troubleshooting_Guide.md` | Common issues |
| `ARCHIVE_INDEX.md` | `docs/99_Archive/ARCHIVE_INDEX.md` | Archive index |

## Python 3.12 Unification Audit

| Location | Previous | Current | Notes |
|----------|----------|---------|-------|
| `environment.yml` | python=3.10 | python=3.12 | Fixed |
| `machine.yaml` | "3.10" | "3.12" | Fixed |
| `scripts/setup_environment.sh` | PYTHON_VERSION="3.10" | PYTHON_VERSION="3.12" | Fixed |
| `scripts/setup_environment_windows.ps1` | N/A (new) | "3.12" | Created with 3.12 |
| `docs/GPU_A_First_Run_Checklist.md` | python=3.10 | Archived | Moved to 99_Archive/ |

**PY312_COMPATIBILITY_BLOCKER:** None detected. All dependencies in requirements.txt and environment.yml declare compatibility with Python 3.12+.
