# Research Agent v3 — Version Information

**Version:** 8.2.2
**Release Date:** 2026-08-16
**Python Version:** 3.12 (conda: research_agent_v3)
**Target Platform:** Windows 10/11 (CPU), Linux + NVIDIA GPU
**Run Modes:** production / limited / development

## Release Contents

- Full source code (13 modules, core, infrastructure, adapters, orchestrator, CLI)
- Configuration files (machine.yaml, storage.yaml, providers.yaml, model_registry.yaml)
- Environment setup scripts (Windows PowerShell + Linux Bash)
- Complete documentation system (01_Deployment through 99_Archive)
- Test suite (literature, reasoning, E2E)
- START_HERE.md as unique entry point

## Capability Levels

| Level | Description | RTX A500 4GB | RTX 3090 24GB |
|-------|-------------|--------------|---------------|
| A | Full Software Pipeline | Supported | Supported |
| B | Full-design Synthetic Research | Supported | Supported |
| C | Small-scale Real Experiment | Conditional | Supported |
| D | Publication-scale Real Experiment | Not supported | Supported (future) |
