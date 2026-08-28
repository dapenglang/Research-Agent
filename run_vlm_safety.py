#!/usr/bin/env python
"""
VLM_Safety_001 Pipeline Runner
Phase 4.9: Run the full research pipeline for VLM Safety task.

Usage:
    conda activate research_agent_v3
    python run_vlm_safety.py
"""

import logging
import sys
import os
from pathlib import Path

# Setup paths
V3_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = V3_ROOT.parent

# Add to sys.path
for p in [str(PROJECT_ROOT), str(V3_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(V3_ROOT / "pipeline_run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("VLM_Safety_001 Pipeline Runner")
    logger.info("Phase 4.9: Running full research pipeline")
    logger.info("=" * 70)

    task_config = V3_ROOT / "configs" / "research_task_vlm_safety.yaml"
    if not task_config.exists():
        logger.error("Task config not found: %s", task_config)
        return 1

    logger.info("Task config: %s", task_config)

    # Change working directory to V3_ROOT
    os.chdir(V3_ROOT)
    logger.info("Working directory: %s", os.getcwd())

    # Import and run pipeline
    from orchestrator.pipeline import PipelineOrchestrator

    logger.info("Initializing PipelineOrchestrator...")
    pipe = PipelineOrchestrator(
        task_config_path=str(task_config),
        state_root=str(V3_ROOT / "state"),
        output_root=str(V3_ROOT / "output"),
    )

    logger.info("Run mode: %s", pipe.run_mode)
    logger.info("Task ID: %s", pipe.task_id)

    # Start pipeline
    logger.info("Starting pipeline...")
    result = pipe.start()

    # Print result
    logger.info("=" * 70)
    logger.info("Pipeline Result:")
    logger.info("  Status: %s", result.get("status"))
    logger.info("  Message: %s", result.get("message"))

    modules_run = result.get("modules_run", [])
    logger.info("  Modules run: %d", len(modules_run))
    for m in modules_run:
        logger.info("    Module %s: status=%s, origin=%s",
                     m.get("module_id"),
                     m.get("status"),
                     m.get("data_origin"))

    if result.get("gate_warnings"):
        logger.warning("  Gate warnings: %d", len(result["gate_warnings"]))
        for w in result["gate_warnings"]:
            logger.warning("    - %s", w)

    if result.get("blocking_errors"):
        logger.error("  Blocking errors: %d", len(result["blocking_errors"]))
        for e in result["blocking_errors"]:
            logger.error("    - %s", e)

    logger.info("=" * 70)

    # Save result to file
    import json
    result_path = V3_ROOT / "pipeline_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Result saved to: %s", result_path)

    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
