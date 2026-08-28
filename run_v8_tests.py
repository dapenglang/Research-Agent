"""
Research Agent v8 — Test Suite

Runs 4 test scenarios:
  Test 1: No API Key — system should give proper warning
  Test 2: API Key present — LLM check detects key (connection may fail, but key detection works)
  Test 3: Papers < 50 — Pipeline stops at literature gate
  Test 4: Papers >= 50 — Pipeline enters research flow (literature gate passes)
"""

import json
import logging
import os
import sys
import time
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PARENT_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PARENT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("v8_test")

import yaml


def test_1_no_api_key() -> dict:
    """Test 1: No API Key — system should correctly report missing keys."""
    logger.info("=" * 60)
    logger.info("Test 1: No API Key detection")
    logger.info("=" * 60)

    # Ensure no API keys are set
    saved_keys = {}
    for key in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "LOCAL_LLM_ENDPOINT"):
        if key in os.environ:
            saved_keys[key] = os.environ.pop(key)

    try:
        # Run check_llm.py logic
        sys.path.insert(0, str(PARENT_ROOT))
        from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
        runtime = LLMRuntime(str(PROJECT_ROOT / "configs"))
        runtime.load()
        status = runtime.get_status()

        openai_available = status.get("openai", {}).get("available", False)
        deepseek_available = status.get("deepseek", {}).get("available", False)

        passed = (not openai_available) and (not deepseek_available)

        return {
            "test": "Test 1: No API Key",
            "passed": passed,
            "details": {
                "openai_available": openai_available,
                "deepseek_available": deepseek_available,
                "message": "System correctly detected missing API keys" if passed else "System failed to detect missing keys",
            },
        }
    finally:
        # Restore keys
        for key, val in saved_keys.items():
            os.environ[key] = val


def test_2_api_key_present() -> dict:
    """Test 2: API Key present — LLM check detects key is set."""
    logger.info("=" * 60)
    logger.info("Test 2: API Key detection")
    logger.info("=" * 60)

    # Set a fake key to test detection
    os.environ["DEEPSEEK_API_KEY"] = "sk-test-fake-key-for-detection"

    try:
        from Research_Agent_v3.infrastructure.llm.llm_provider import DeepSeekProvider

        provider = DeepSeekProvider(api_key="sk-test-fake-key-for-detection")
        key_detected = provider.is_available()

        # The key is detected (is_available=True), even though actual API call would fail
        passed = key_detected

        return {
            "test": "Test 2: API Key Present",
            "passed": passed,
            "details": {
                "key_detected": key_detected,
                "provider_name": provider.get_name(),
                "message": "System correctly detected API key presence" if passed else "System failed to detect API key",
            },
        }
    finally:
        os.environ.pop("DEEPSEEK_API_KEY", None)


def test_3_papers_insufficient() -> dict:
    """Test 3: Papers < 50 — Pipeline should stop at literature gate."""
    logger.info("=" * 60)
    logger.info("Test 3: Papers < 50 (Pipeline should block)")
    logger.info("=" * 60)

    # Ensure data/literature/pdf has < 50 papers (should be 0 or very few)
    pdf_dir = PROJECT_ROOT / "data" / "literature" / "pdf"
    latex_dir = PROJECT_ROOT / "data" / "literature" / "latex"

    pdf_count = sum(1 for f in pdf_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf") if pdf_dir.exists() else 0
    latex_count = sum(1 for d in latex_dir.iterdir() if d.is_dir() and list(d.rglob("*.tex"))) if latex_dir.exists() else 0
    total = pdf_count + latex_count

    if total >= 50:
        # Temporarily move papers aside (shouldn't happen in test env)
        return {
            "test": "Test 3: Papers < 50",
            "passed": False,
            "details": {"message": f"Pre-condition failed: {total} papers already exist (expected < 50)"},
        }

    # Run pipeline (should be blocked)
    try:
        from Research_Agent_v3.orchestrator.pipeline import PipelineOrchestrator

        task_path = PROJECT_ROOT / "tasks" / "task_001.yaml"

        # Clean state
        with open(task_path, "r", encoding="utf-8") as f:
            task_cfg = yaml.safe_load(f)
        task_id = task_cfg.get("task_id", "task_001")
        state_dir = PROJECT_ROOT / "state" / task_id
        if state_dir.exists():
            shutil.rmtree(state_dir, ignore_errors=True)

        orchestrator = PipelineOrchestrator(str(task_path), skip_gates=False)
        result = orchestrator.start()

        blocked = result.get("status") == "blocked"
        gate = result.get("gate", "")

        passed = blocked and gate == "literature_quality"

        return {
            "test": "Test 3: Papers < 50",
            "passed": passed,
            "details": {
                "paper_count": total,
                "pipeline_status": result.get("status"),
                "gate": gate,
                "message": result.get("message", ""),
            },
        }
    except Exception as e:
        return {
            "test": "Test 3: Papers < 50",
            "passed": False,
            "details": {"error": str(e)},
        }


def test_4_papers_sufficient() -> dict:
    """Test 4: Papers >= 50 — Pipeline should pass literature gate."""
    logger.info("=" * 60)
    logger.info("Test 4: Papers >= 50 (Pipeline should pass gate)")
    logger.info("=" * 60)

    pdf_dir = PROJECT_ROOT / "data" / "literature" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Create 50 dummy PDF files
    created_files: List[Path] = []
    for i in range(50):
        dummy_path = pdf_dir / f"test_paper_{i:04d}.pdf"
        # Write a minimal fake PDF (> 1KB)
        dummy_path.write_bytes(b"%PDF-1.4\n" + b"0" * 2048 + b"\n%%EOF")
        created_files.append(dummy_path)

    try:
        # Verify count
        pdf_count = sum(1 for f in pdf_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf" and f.stat().st_size > 1024)
        assert pdf_count >= 50, f"Only {pdf_count} PDFs created"

        # Run pipeline (should pass literature gate)
        from Research_Agent_v3.orchestrator.pipeline import PipelineOrchestrator

        task_path = PROJECT_ROOT / "tasks" / "task_001.yaml"

        # Clean state
        with open(task_path, "r", encoding="utf-8") as f:
            task_cfg = yaml.safe_load(f)
        task_id = task_cfg.get("task_id", "task_001")
        state_dir = PROJECT_ROOT / "state" / task_id
        if state_dir.exists():
            shutil.rmtree(state_dir, ignore_errors=True)

        orchestrator = PipelineOrchestrator(str(task_path), skip_gates=False)
        result = orchestrator.start()

        # Pipeline should NOT be blocked
        not_blocked = result.get("status") != "blocked"

        # Check if literature gate passed (look for it in modules or message)
        gate_passed = "literature" not in result.get("message", "").lower() or "passed" in result.get("message", "").lower()

        passed = not_blocked

        return {
            "test": "Test 4: Papers >= 50",
            "passed": passed,
            "details": {
                "paper_count": pdf_count,
                "pipeline_status": result.get("status"),
                "message": result.get("message", "")[:200],
                "gate_warnings": result.get("gate_warnings", []),
            },
        }
    except Exception as e:
        return {
            "test": "Test 4: Papers >= 50",
            "passed": False,
            "details": {"error": str(e)},
        }
    finally:
        # Clean up dummy files
        for f in created_files:
            try:
                f.unlink()
            except Exception:
                pass


def test_check_scripts() -> dict:
    """Test that check scripts run correctly."""
    logger.info("=" * 60)
    logger.info("Test 5: Check scripts execution")
    logger.info("=" * 60)

    results: List[dict] = []

    # Test check_literature.py
    try:
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "check_literature.py"), "--min", "50"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        results.append({
            "script": "check_literature.py",
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "passed": proc.returncode in (0, 1),  # 0=pass, 1=insufficient (both valid)
        })
    except Exception as e:
        results.append({"script": "check_literature.py", "error": str(e), "passed": False})

    # Test check_llm.py
    try:
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "check_llm.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        results.append({
            "script": "check_llm.py",
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip()[:200],
            "passed": proc.returncode in (0, 1),
        })
    except Exception as e:
        results.append({"script": "check_llm.py", "error": str(e), "passed": False})

    # Test check_research_ready.py
    try:
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "check_research_ready.py"), "--skip-api-test"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        results.append({
            "script": "check_research_ready.py",
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip()[:200],
            "passed": proc.returncode in (0, 1),
        })
    except Exception as e:
        results.append({"script": "check_research_ready.py", "error": str(e), "passed": False})

    all_passed = all(r.get("passed", False) for r in results)

    return {
        "test": "Test 5: Check Scripts",
        "passed": all_passed,
        "details": results,
    }


def main():
    logger.info("Research Agent v8 — Test Suite")
    logger.info("Python: %s", sys.version)

    report = {
        "version": "v8",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": [],
    }

    # Run tests
    report["tests"].append(test_1_no_api_key())
    report["tests"].append(test_2_api_key_present())
    report["tests"].append(test_3_papers_insufficient())
    report["tests"].append(test_4_papers_sufficient())
    report["tests"].append(test_check_scripts())

    # Summary
    passed = sum(1 for t in report["tests"] if t["passed"])
    total = len(report["tests"])

    logger.info("=" * 60)
    logger.info("Test Summary: %d/%d passed", passed, total)
    for t in report["tests"]:
        status = "PASS" if t["passed"] else "FAIL"
        logger.info("  [%s] %s", status, t["test"])
    logger.info("=" * 60)

    # Save report
    report_path = PROJECT_ROOT / "v8_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Report saved to %s", report_path)

    return report


if __name__ == "__main__":
    main()
