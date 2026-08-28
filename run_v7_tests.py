"""
Research Agent v7 — Full Pipeline Test Runner

Runs the complete pipeline for task_001 and task_002 in synthetic_research mode,
collects results, and outputs a structured test summary.
"""

import json
import logging
import os
import sys
import time
import shutil
from pathlib import Path

# Project root (D:\Research Agent\Research_Agent_v3)
# Parent (D:\Research Agent) must be on path so `Research_Agent_v3` is importable as a package
PROJECT_ROOT = Path(__file__).resolve().parent
_PARENT_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(_PARENT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("v7_test_runner")

from Research_Agent_v3.orchestrator.pipeline import PipelineOrchestrator


EXPECTED_MODULES = [
    "01", "02", "02_5", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13",
]


def run_task(task_file: str) -> dict:
    """Run a single task through the pipeline and return results."""
    task_path = PROJECT_ROOT / "tasks" / task_file
    if not task_path.exists():
        return {"task": task_file, "status": "ERROR", "message": f"Task file not found: {task_path}"}

    # Parse task_id from YAML to clean the correct state directory
    import yaml as yaml_mod
    with open(task_path, "r", encoding="utf-8") as f:
        task_cfg = yaml_mod.safe_load(f)
    task_id = task_cfg.get("task_id", task_file.replace(".yaml", ""))

    state_dir = PROJECT_ROOT / "state" / task_id
    output_dir = PROJECT_ROOT / "output"

    if state_dir.exists():
        shutil.rmtree(state_dir, ignore_errors=True)

    logger.info("=" * 60)
    logger.info("Starting pipeline for %s", task_file)
    logger.info("=" * 60)

    start_time = time.time()

    try:
        orchestrator = PipelineOrchestrator(
            task_config_path=str(task_path),
            state_root=str(PROJECT_ROOT / "state"),
            output_root=str(output_dir),
        )
        result = orchestrator.start()
        elapsed = time.time() - start_time

        modules_run = result.get("modules_run", [])
        module_summary = []
        for m in modules_run:
            module_summary.append({
                "module_id": m.get("module_id"),
                "status": m.get("status"),
                "data_origin": m.get("data_origin"),
                "output_file_count": len(m.get("output_files", {})),
            })

        passed = sum(1 for m in module_summary if m["status"] == "PASS")
        warnings = sum(1 for m in module_summary if m["status"] == "WARNING")
        failed = sum(1 for m in module_summary if m["status"] == "FAIL")
        skipped = sum(1 for m in module_summary if m["status"] == "SKIPPED")

        return {
            "task": task_file,
            "status": result.get("status", "unknown"),
            "elapsed_seconds": round(elapsed, 2),
            "modules": module_summary,
            "summary": {
                "total": len(module_summary),
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "skipped": skipped,
            },
            "provenance_count": len(result.get("provenance", [])),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("Pipeline failed for %s: %s", task_file, e, exc_info=True)
        return {
            "task": task_file,
            "status": "FAILED",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e),
        }


def check_outputs() -> dict:
    """Check generated output files."""
    output_dir = PROJECT_ROOT / "output"
    checks = {}

    # Check paper outputs
    paper_dir = output_dir / "paper"
    checks["paper_dir_exists"] = paper_dir.exists()
    if paper_dir.exists():
        paper_files = list(paper_dir.rglob("*"))
        checks["paper_files"] = [str(f.relative_to(output_dir)) for f in paper_files if f.is_file()]

    # Check references
    ref_dir = output_dir / "references"
    checks["ref_dir_exists"] = ref_dir.exists()
    if ref_dir.exists():
        ref_files = list(ref_dir.rglob("*"))
        checks["ref_files"] = [str(f.relative_to(output_dir)) for f in ref_files if f.is_file()]

    # Check figures/tables
    fig_dir = output_dir / "figures_tables"
    checks["fig_dir_exists"] = fig_dir.exists()
    if fig_dir.exists():
        fig_files = list(fig_dir.rglob("*"))
        checks["fig_files"] = [str(f.relative_to(output_dir)) for f in fig_files if f.is_file()]

    # Check analysis
    analysis_dir = output_dir / "analysis"
    checks["analysis_dir_exists"] = analysis_dir.exists()
    if analysis_dir.exists():
        analysis_files = list(analysis_dir.rglob("*"))
        checks["analysis_files"] = [str(f.relative_to(output_dir)) for f in analysis_files if f.is_file()]

    return checks


def check_llm_runtime() -> dict:
    """Check LLM runtime status."""
    try:
        from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
        runtime = LLMRuntime()
        runtime.load()
        status = runtime.get_status()
        return {"status": "ok", "providers": status}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_memory_system() -> dict:
    """Check Research Memory system."""
    memory_dir = PROJECT_ROOT / "memory"
    checks = {
        "memory_dir_exists": memory_dir.exists(),
    }
    if memory_dir.exists():
        subdirs = [d.name for d in memory_dir.iterdir() if d.is_dir()]
        checks["subdirs"] = subdirs
        all_files = list(memory_dir.rglob("*.json")) + list(memory_dir.rglob("*.jsonl"))
        checks["total_files"] = len(all_files)
    return checks


def check_configs() -> dict:
    """Check all config files are loadable."""
    import yaml
    configs_dir = PROJECT_ROOT / "configs"
    results = {}
    for cfg_file in sorted(configs_dir.glob("*.yaml")):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
            results[cfg_file.name] = "OK"
        except Exception as e:
            results[cfg_file.name] = f"FAIL: {e}"
    return results


def main():
    logger.info("Research Agent v7 — Full Pipeline Test")
    logger.info("Python: %s", sys.version)
    logger.info("Project root: %s", PROJECT_ROOT)

    report = {
        "version": "v7",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version,
    }

    # 1. Config validation
    logger.info("--- Step 1: Config Validation ---")
    report["configs"] = check_configs()

    # 2. LLM Runtime check
    logger.info("--- Step 2: LLM Runtime Check ---")
    report["llm_runtime"] = check_llm_runtime()

    # 3. Memory system check
    logger.info("--- Step 3: Memory System Check ---")
    report["memory_system"] = check_memory_system()

    # 4. Run task_001
    logger.info("--- Step 4: Pipeline Run (task_001) ---")
    report["task_001"] = run_task("task_001.yaml")

    # 5. Run task_002
    logger.info("--- Step 5: Pipeline Run (task_002) ---")
    report["task_002"] = run_task("task_002.yaml")

    # 6. Output verification
    logger.info("--- Step 6: Output Verification ---")
    report["outputs"] = check_outputs()

    # Summary
    logger.info("--- Summary ---")
    t1 = report["task_001"]
    t2 = report["task_002"]
    logger.info("Task 001: %s (%.1fs) — PASS=%d WARN=%d FAIL=%d SKIP=%d",
                t1.get("status"), t1.get("elapsed_seconds", 0),
                t1.get("summary", {}).get("passed", 0),
                t1.get("summary", {}).get("warnings", 0),
                t1.get("summary", {}).get("failed", 0),
                t1.get("summary", {}).get("skipped", 0))
    logger.info("Task 002: %s (%.1fs) — PASS=%d WARN=%d FAIL=%d SKIP=%d",
                t2.get("status"), t2.get("elapsed_seconds", 0),
                t2.get("summary", {}).get("passed", 0),
                t2.get("summary", {}).get("warnings", 0),
                t2.get("summary", {}).get("failed", 0),
                t2.get("summary", {}).get("skipped", 0))

    # Save report
    report_path = PROJECT_ROOT / "v7_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Test report saved to %s", report_path)

    return report


if __name__ == "__main__":
    main()
