# Archive Index — Research Agent v3

**Date:** 2026-08-15

This directory contains historical documents that have been superseded by the final release documentation. These files are retained for historical reference only.

**Do NOT use these documents for current deployment.** See `START_HERE.md` for the current entry point.

---

## Archived Documents

| File | Original Path | Status | Superseded By |
|------|---------------|--------|---------------|
| `GPU_A_First_Run_Checklist.md` | `docs/GPU_A_First_Run_Checklist.md` | ARCHIVED | `docs/01_Deployment/Windows_Deployment_Guide.md` |
| `README_GPU_A.md` | `docs/README_GPU_A.md` | ARCHIVED | `docs/01_Deployment/Windows_Deployment_Guide.md` |

---

## Archive Notes

### GPU_A_First_Run_Checklist.md
- **Original Purpose:** Checklist for first run on GPU_A server (Linux)
- **Why Archived:** Content has been integrated into the Windows Deployment Guide. The original referenced Python 3.10 (now unified to 3.12) and targeted a Linux GPU server (GPU_A). The current release targets Windows 10/11 with RTX A500.
- **Still Valid Content:** General pipeline testing approach, verification steps (concept applicable).

### README_GPU_A.md
- **Original Purpose:** Migration guide for GPU_A server deployment
- **Why Archived:** Content has been superseded by the comprehensive Windows Deployment Guide. The original targeted a Linux GPU server and referenced the Phase E Migration Package.
- **Still Valid Content:** General architecture overview, module descriptions (concept applicable).

---

## Phase A-E Implementation Reports

Phase A-E implementation reports (if generated during development) are also historical development records. They document the modularization process and are NOT needed for deployment.

For current deployment, use only:
- `START_HERE.md` — Entry point
- `docs/01_Deployment/` — Deployment guides
- `docs/02_Usage/` — Usage guides
- `docs/03_Configuration/` — Configuration guides
- `docs/04_Troubleshooting/` — Troubleshooting
