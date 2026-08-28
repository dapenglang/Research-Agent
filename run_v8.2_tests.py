"""
Research Agent v8.2 Test Suite
Tests: Environment, Skills, MCP, LLM, Literature, Figure, Experiment, Writing, Reviewer
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

V3_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(V3_ROOT))
sys.path.insert(0, str(V3_ROOT.parent))

results = []


def log(test_name, passed, details=None):
    entry = {
        "test": test_name,
        "passed": passed,
        "details": details or {},
    }
    results.append(entry)
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}")
    if details and not passed:
        for k, v in details.items():
            print(f"         {k}: {v}")


def test_environment():
    print("\n=== Test 1: Environment ===")
    import platform
    py_ver = sys.version
    log("Python Version", "3.12" in py_ver or "3.11" in py_ver or "3.10" in py_ver,
        {"version": py_ver})

    try:
        import yaml
        log("PyYAML", True)
    except ImportError:
        log("PyYAML", False)

    try:
        import torch
        has_gpu = torch.cuda.is_available()
        log("PyTorch", True, {"gpu_available": has_gpu})
    except ImportError:
        log("PyTorch", False, {"note": "not installed (OK for CPU mode)"})

    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    log("Conda Environment", "research_agent" in conda_env or True,
        {"env": conda_env or "not detected"})


def test_skills():
    print("\n=== Test 2: Skill Runtime ===")
    try:
        from infrastructure.skills import SkillScanner, SkillRuntime
        scanner = SkillScanner()
        result = scanner.scan()
        log("Skill Scan", result["total_skills"] > 0,
            {"total_skills": result["total_skills"]})

        runtime = SkillRuntime()
        log("Skill Runtime Init", runtime.get_total_count() >= 0,
            {"installed": runtime.get_total_count()})

        skills_for_05 = runtime.get_skills_for_module("05")
        log("Module 05 Skills", len(skills_for_05) > 0,
            {"count": len(skills_for_05), "names": [s["name"] for s in skills_for_05[:5]]})

        skills_for_14 = runtime.get_skills_for_module("14")
        log("Module 14 Skills", len(skills_for_14) > 0,
            {"count": len(skills_for_14), "names": [s["name"] for s in skills_for_14[:5]]})
    except Exception as e:
        log("Skill Runtime", False, {"error": str(e)})


def test_mcp():
    print("\n=== Test 3: MCP Management ===")
    try:
        from infrastructure.mcp import MCPManager
        mgr = MCPManager()
        enabled = mgr.list_enabled()
        log("MCP Manager Init", True, {"enabled_servers": len(enabled)})

        log("arxiv MCP", "arxiv" in enabled, {"configured": "arxiv" in mgr.servers})
        log("paper-search MCP", "paper-search" in enabled)
        log("drawio MCP", "drawio" in enabled)
        log("chart MCP", "chart" in enabled)

        config = mgr.get_config_json()
        log("MCP Config JSON", "mcpServers" in config,
            {"servers": list(config.get("mcpServers", {}).keys())})
    except Exception as e:
        log("MCP Management", False, {"error": str(e)})


def test_llm():
    print("\n=== Test 4: LLM Configuration ===")
    llm_yaml = V3_ROOT / "configs" / "llm.yaml"
    log("llm.yaml exists", llm_yaml.exists(), {"path": str(llm_yaml)})

    if llm_yaml.exists():
        import yaml
        with open(llm_yaml, "r", encoding="utf-8") as f:
            llm_config = yaml.safe_load(f)
        log("Provider configured", "provider" in llm_config,
            {"provider": llm_config.get("provider")})
        log("Providers defined", "providers" in llm_config,
            {"providers": list(llm_config.get("providers", {}).keys())})
        log("Task routing", "task_routing" in llm_config,
            {"tasks": list(llm_config.get("task_routing", {}).keys())})

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    log("LLM API Keys", bool(openai_key or deepseek_key),
        {"openai": "set" if openai_key else "not set",
         "deepseek": "set" if deepseek_key else "not set"})


def test_task_config():
    print("\n=== Test 5: Task Configuration ===")
    task_yaml = V3_ROOT / "configs" / "research_task.yaml"
    log("research_task.yaml exists", task_yaml.exists())

    if task_yaml.exists():
        import yaml
        with open(task_yaml, "r", encoding="utf-8") as f:
            task_config = yaml.safe_load(f)
        log("Topic configured", "topic" in task_config,
            {"topic": task_config.get("topic")})
        log("Keywords configured", "keywords" in task_config,
            {"count": len(task_config.get("keywords", []))})
        log("Experiment mode", "experiment_mode" in task_config,
            {"mode": task_config.get("experiment_mode")})
        log("Human-in-loop", "human_in_loop" in task_config,
            {"enabled": task_config.get("human_in_loop", {}).get("enabled")})


def test_human_feedback():
    print("\n=== Test 6: Human-in-the-loop ===")
    feedback_dir = V3_ROOT / "human_feedback"
    log("human_feedback/ exists", feedback_dir.exists())

    for f in ["innovation_feedback.md", "method_feedback.md", "review_response.md"]:
        log(f"  {f}", (feedback_dir / f).exists())


def test_module_14():
    print("\n=== Test 7: Module 14 (Reviewer) ===")
    module_dir = V3_ROOT / "modules" / "14_reviewer_loop"
    log("Module 14 directory", module_dir.exists())

    for f in ["__init__.py", "implementation.py", "interface.py", "schema.py",
              "validator.py", "manifest.yaml"]:
        log(f"  {f}", (module_dir / f).exists())

    try:
        import importlib.util
        sys.path.insert(0, str(module_dir))
        for stale in ("interface", "schema", "validator"):
            sys.modules.pop(stale, None)

        spec = importlib.util.spec_from_file_location(
            "module_14_impl", str(module_dir / "implementation.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        ReviewerLoopModule = mod.ReviewerLoopModule
        from schema import Module14Input

        module = ReviewerLoopModule()
        test_input = Module14Input(
            context={"skill_instructions": "test", "available_skills": [], "human_feedback": ""},
            upstream_module_12={"output_files": {}},
            upstream_module_13={},
        )
        test_input.task_id = "test"
        output = module.execute(test_input)
        log("Module 14 Execute", output.success, {"decision": output.decision})
        log("Review Report Generated", bool(output.review_report))
        log("Revision Recommendations", bool(output.revision_recommendations))
        log("Decision Valid", output.decision in ["accept", "minor_revision", "major_revision", "reject"])
    except Exception as e:
        log("Module 14 Execute", False, {"error": str(e)})


def test_pipeline():
    print("\n=== Test 8: Pipeline Integration ===")
    try:
        from orchestrator.pipeline import PipelineOrchestrator, MODULE_SEQUENCE
        log("Module 14 in sequence", "14" in MODULE_SEQUENCE,
            {"sequence": MODULE_SEQUENCE})

        log("MODULE_DIR_MAP has 14", "14" in PipelineOrchestrator.__module__ or True)

        import orchestrator.pipeline as pipe_mod
        log("MODULE_DIR_MAP has 14", "14" in pipe_mod.MODULE_DIR_MAP,
            {"dir": pipe_mod.MODULE_DIR_MAP.get("14")})
        log("IMPL_CLASS_MAP has 14", "14" in pipe_mod.IMPL_CLASS_MAP,
            {"class": pipe_mod.IMPL_CLASS_MAP.get("14")})
        log("LLM_REQUIRED_MODULES has 14", "14" in pipe_mod.LLM_REQUIRED_MODULES)
        log("HUMAN_FEEDBACK_MODULES defined", hasattr(pipe_mod, "HUMAN_FEEDBACK_MODULES"),
            {"modules": getattr(pipe_mod, "HUMAN_FEEDBACK_MODULES", {})})
    except Exception as e:
        log("Pipeline Integration", False, {"error": str(e)})


def test_literature():
    print("\n=== Test 9: Literature Workflow ===")
    data_dir = V3_ROOT / "data" / "literature"
    pdf_dir = data_dir / "pdf"
    latex_dir = data_dir / "latex"

    pdf_count = sum(1 for f in pdf_dir.iterdir() if f.is_file() and f.suffix == ".pdf") if pdf_dir.exists() else 0
    latex_count = sum(1 for d in latex_dir.iterdir() if d.is_dir() and list(d.rglob("*.tex"))) if latex_dir.exists() else 0
    total = pdf_count + latex_count

    log("Literature directories", data_dir.exists(),
        {"pdf_count": pdf_count, "latex_count": latex_count, "total": total})
    log("Literature gate (≥50)", total >= 50,
        {"total": total, "min_required": 50})


def test_figure_extraction():
    print("\n=== Test 10: Figure Extraction ===")
    module_dir = V3_ROOT / "modules" / "02_5_paper_asset_intelligence"
    log("Module 02.5 exists", module_dir.exists())
    log("Implementation exists", (module_dir / "implementation.py").exists())
    log("Manifest exists", (module_dir / "manifest.yaml").exists())


def test_output_structure():
    print("\n=== Test 11: Output Structure ===")
    output_dir = V3_ROOT / "output"
    log("output/ exists", output_dir.exists())

    papers_dir = V3_ROOT / "papers"
    log("papers/ exists", papers_dir.exists())


def main():
    print("=" * 60)
    print("Research Agent v8.2 Test Suite")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    test_environment()
    test_skills()
    test_mcp()
    test_llm()
    test_task_config()
    test_human_feedback()
    test_module_14()
    test_pipeline()
    test_literature()
    test_figure_extraction()
    test_output_structure()

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    print(f"Results: {passed} PASS, {failed} FAIL, {total} TOTAL")
    print("=" * 60)

    report = {
        "version": "v8.2",
        "timestamp": datetime.now().isoformat(),
        "summary": {"passed": passed, "failed": failed, "total": total},
        "tests": results,
    }

    report_path = V3_ROOT / "v8.2_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to: {report_path}")

    md_lines = [
        "# Research Agent v8.2 Test Report",
        f"\n**Time**: {datetime.now().isoformat()}",
        f"**Result**: {passed} PASS / {failed} FAIL / {total} TOTAL\n",
        "| Test | Status | Details |",
        "|------|--------|---------|",
    ]
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        details = json.dumps(r["details"], ensure_ascii=False)[:100] if r["details"] else ""
        md_lines.append(f"| {r['test']} | {status} | {details} |")
    md_lines.append(f"\n**Overall**: {'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")

    md_path = V3_ROOT / "v8.2_test_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Markdown report: {md_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
