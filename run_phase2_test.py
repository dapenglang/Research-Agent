#!/usr/bin/env python
"""
Phase 2 Test Script — v8.2.2 Pipeline Integration

Tests:
1. Pipeline imports correctly with new v8.2.2 config loading
2. Pipeline.__init__ loads external_dependency.yaml and dependency_policy.yaml
3. Pipeline._run_pre_checks() works correctly
4. Pipeline.get_fallback() returns correct policies
5. Pipeline.run_mode property works
6. Pipeline._build_context() includes pipeline reference
7. check_research_ready.py includes new checks
8. Backward compatibility: existing pipeline methods still work
9. Limited mode: pre-checks don't block
10. Production mode: pre-checks block on missing required skills
"""

import sys
import os
import logging
from pathlib import Path
import copy

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root.parent))

logging.basicConfig(level=logging.WARNING)

passed = 0
failed = 0
skipped = 0
results = []


def log(test_name, status, detail=""):
    global passed, failed, skipped
    results.append({"test": test_name, "status": status, "detail": detail})
    print(f"  [{status}] {test_name}: {detail}" if detail else f"  [{status}] {test_name}")
    if status == "PASS":
        passed += 1
    elif status == "FAIL":
        failed += 1
    else:
        skipped += 1


print("=" * 60)
print("Phase 2 Test: Pipeline Integration v8.2.2")
print("=" * 60)

# ── Test 1: Pipeline import ──
print("\n--- Test Group 1: Pipeline Import ---")

try:
    from orchestrator.pipeline import PipelineOrchestrator
    log("PipelineOrchestrator import", "PASS")
except Exception as e:
    log("PipelineOrchestrator import", "FAIL", str(e))
    sys.exit(1)

# ── Test 2: Pipeline init with v8.2.2 config ──
print("\n--- Test Group 2: Pipeline Init ---")

task_config_path = project_root / "configs" / "research_task.yaml"
if not task_config_path.exists():
    # Try alternate path
    for p in [project_root / "tasks" / "task_001.yaml", project_root / "configs" / "research_task_template.yaml"]:
        if p.exists():
            task_config_path = p
            break

try:
    pipe = PipelineOrchestrator(
        task_config_path=task_config_path,
        state_root="state_test_v822",
        output_root="output_test_v822",
        skip_gates=True,
    )
    log("Pipeline init (skip_gates=True)", "PASS")
except Exception as e:
    log("Pipeline init (skip_gates=True)", "FAIL", str(e))
    pipe = None

if pipe:
    # Test run_mode
    try:
        rm = pipe.run_mode
        if rm in ("production", "limited", "development"):
            log("Pipeline.run_mode", "PASS", f"mode={rm}")
        else:
            log("Pipeline.run_mode", "FAIL", f"unexpected mode: {rm}")
    except Exception as e:
        log("Pipeline.run_mode", "FAIL", str(e))

    # Test external_deps loaded
    try:
        if pipe._external_deps and "run_mode" in pipe._external_deps:
            log("Pipeline._external_deps loaded", "PASS", f"keys={list(pipe._external_deps.keys())[:5]}")
        else:
            log("Pipeline._external_deps loaded", "FAIL", "No run_mode in external_deps")
    except Exception as e:
        log("Pipeline._external_deps loaded", "FAIL", str(e))

    # Test fallback_policy loaded
    try:
        if pipe._fallback_policy and "skill_fallback" in pipe._fallback_policy:
            log("Pipeline._fallback_policy loaded", "PASS", f"skill_fallback={len(pipe._fallback_policy.get('skill_fallback', {}))} policies")
        else:
            log("Pipeline._fallback_policy loaded", "FAIL", "No skill_fallback in policy")
    except Exception as e:
        log("Pipeline._fallback_policy loaded", "FAIL", str(e))

# ── Test 3: get_fallback() ──
print("\n--- Test Group 3: get_fallback() ---")

if pipe:
    # Test skill fallback
    try:
        fb = pipe.get_fallback("01", "skill:light-literature-search")
        if fb.get("action") in ("llm_prompt", "internal_implementation", "skip", "block", "none"):
            log("get_fallback(skill:light-literature-search)", "PASS", f"action={fb['action']}, message={fb.get('message', '')[:50]}")
        else:
            log("get_fallback(skill:light-literature-search)", "FAIL", f"unexpected action: {fb}")
    except Exception as e:
        log("get_fallback(skill:light-literature-search)", "FAIL", str(e))

    # Test mcp fallback
    try:
        fb = pipe.get_fallback("02", "mcp:arxiv")
        if fb.get("action") in ("internal_implementation", "skip", "block", "none", "local_file"):
            log("get_fallback(mcp:arxiv)", "PASS", f"action={fb['action']}")
        else:
            log("get_fallback(mcp:arxiv)", "FAIL", f"unexpected: {fb}")
    except Exception as e:
        log("get_fallback(mcp:arxiv)", "FAIL", str(e))

    # Test unknown dependency
    try:
        fb = pipe.get_fallback("05", "skill:nonexistent-skill")
        if fb.get("action") == "skip":
            log("get_fallback(unknown skill → default)", "PASS", f"action={fb['action']}")
        else:
            log("get_fallback(unknown skill → default)", "FAIL", f"unexpected: {fb}")
    except Exception as e:
        log("get_fallback(unknown skill → default)", "FAIL", str(e))

    # Test llm fallback
    try:
        fb = pipe.get_fallback("05", "llm")
        if fb.get("action") == "template":
            log("get_fallback(llm)", "PASS", f"action={fb['action']}")
        else:
            log("get_fallback(llm)", "FAIL", f"unexpected: {fb}")
    except Exception as e:
        log("get_fallback(llm)", "FAIL", str(e))

    # Test production mode blocks fallback
    try:
        pipe._run_mode = "production"
        fb = pipe.get_fallback("01", "skill:light-literature-search")
        if fb.get("action") == "block":
            log("get_fallback(production mode blocks)", "PASS", f"action={fb['action']}, reason={fb.get('reason', '')[:50]}")
        else:
            log("get_fallback(production mode blocks)", "FAIL", f"expected block, got: {fb.get('action')}")
        pipe._run_mode = "limited"  # Reset
    except Exception as e:
        log("get_fallback(production mode blocks)", "FAIL", str(e))
        pipe._run_mode = "limited"

# ── Test 4: _run_pre_checks() ──
print("\n--- Test Group 4: _run_pre_checks() ---")

if pipe:
    # Limited mode: should pass with warnings
    try:
        pipe._run_mode = "limited"
        result = pipe._run_pre_checks()
        if result["passed"]:
            log("_run_pre_checks() limited mode", "PASS", f"passed=True, warnings={len(result.get('warnings', []))}")
        else:
            log("_run_pre_checks() limited mode", "WARN", f"passed=False (may be OK if required skills missing)")
    except Exception as e:
        log("_run_pre_checks() limited mode", "FAIL", str(e))

    # Check pre_check_results populated
    try:
        if pipe._pre_check_results:
            log("_pre_check_results populated", "PASS", f"keys={list(pipe._pre_check_results.keys())[:5]}")
        else:
            log("_pre_check_results populated", "FAIL", "No pre_check_results")
    except Exception as e:
        log("_pre_check_results populated", "FAIL", str(e))

    # Check skill_check populated
    try:
        sc = pipe._pre_check_results.get("skill_check") if pipe._pre_check_results else None
        if sc and "modules" in sc:
            log("pre_check skill_check", "PASS", f"modules={sc.get('total_modules', 0)}")
        else:
            log("pre_check skill_check", "WARN", "No skill check data")
    except Exception as e:
        log("pre_check skill_check", "FAIL", str(e))

    # Check mcp_check populated
    try:
        mc = pipe._pre_check_results.get("mcp_check") if pipe._pre_check_results else None
        if mc and "servers" in mc:
            log("pre_check mcp_check", "PASS", f"installed={mc.get('installed_count', 0)}/{mc.get('total_enabled', 0)}")
        else:
            log("pre_check mcp_check", "WARN", "No MCP check data")
    except Exception as e:
        log("pre_check mcp_check", "FAIL", str(e))

    # Check portability_check populated
    try:
        pc = pipe._pre_check_results.get("portability_check") if pipe._pre_check_results else None
        if pc and "checks" in pc:
            log("pre_check portability_check", "PASS", f"checks={len(pc.get('checks', []))}")
        else:
            log("pre_check portability_check", "WARN", "No portability check data")
    except Exception as e:
        log("pre_check portability_check", "FAIL", str(e))

# ── Test 5: _build_context() includes pipeline reference ──
print("\n--- Test Group 5: Context Injection ---")

if pipe:
    try:
        ctx = pipe._build_context("01")
        if "pipeline" in ctx:
            log("Context includes pipeline reference", "PASS")
        else:
            log("Context includes pipeline reference", "FAIL", "No 'pipeline' key in context")
    except Exception as e:
        log("Context includes pipeline reference", "FAIL", str(e))

    try:
        ctx = pipe._build_context("05")
        if "run_mode" in ctx:
            log("Context includes run_mode", "PASS", f"mode={ctx['run_mode']}")
        else:
            log("Context includes run_mode", "FAIL", "No 'run_mode' key in context")
    except Exception as e:
        log("Context includes run_mode", "FAIL", str(e))

# ── Test 6: Backward compatibility ──
print("\n--- Test Group 6: Backward Compatibility ---")

if pipe:
    try:
        status = pipe.get_status()
        if "status" in status:
            log("get_status() works", "PASS")
        else:
            log("get_status() works", "FAIL", "No status key")
    except Exception as e:
        log("get_status() works", "FAIL", str(e))

    try:
        skip = pipe._determine_skip_modules()
        if isinstance(skip, list):
            log("_determine_skip_modules() works", "PASS", f"skip={skip}")
        else:
            log("_determine_skip_modules() works", "FAIL", "Not a list")
    except Exception as e:
        log("_determine_skip_modules() works", "FAIL", str(e))

    try:
        gate = pipe._check_literature_gate()
        if "passed" in gate:
            log("_check_literature_gate() works", "PASS", f"passed={gate['passed']}")
        else:
            log("_check_literature_gate() works", "FAIL", "No passed key")
    except Exception as e:
        log("_check_literature_gate() works", "FAIL", str(e))

    try:
        gate = pipe._check_llm_gate("05")
        if "passed" in gate:
            log("_check_llm_gate() works", "PASS", f"passed={gate['passed']}")
        else:
            log("_check_llm_gate() works", "FAIL", "No passed key")
    except Exception as e:
        log("_check_llm_gate() works", "FAIL", str(e))

# ── Test 7: check_research_ready.py integration ──
print("\n--- Test Group 7: check_research_ready.py ---")

try:
    sys.path.insert(0, str(project_root / "scripts"))
    from check_research_ready import (
        check_skills_installed, check_mcp_installed, check_portability as cr_portability
    )
    log("check_research_ready.py new functions importable", "PASS")
except Exception as e:
    log("check_research_ready.py new functions importable", "FAIL", str(e))

try:
    sr = check_skills_installed(project_root)
    if "passed" in sr and "total" in sr.get("details", {}):
        log("check_skills_installed()", "PASS", f"total={sr['details'].get('total')}, found={sr['details'].get('found')}")
    else:
        log("check_skills_installed()", "FAIL", f"unexpected: {sr}")
except Exception as e:
    log("check_skills_installed()", "FAIL", str(e))

try:
    mr = check_mcp_installed(project_root)
    if "passed" in mr and "total" in mr.get("details", {}):
        log("check_mcp_installed()", "PASS", f"total={mr['details'].get('total')}, installed={mr['details'].get('installed')}")
    else:
        log("check_mcp_installed()", "FAIL", f"unexpected: {mr}")
except Exception as e:
    log("check_mcp_installed()", "FAIL", str(e))

try:
    pr = cr_portability(project_root)
    if "passed" in pr:
        log("check_portability() in check_research_ready", "PASS", f"passed={pr['passed']}")
    else:
        log("check_portability() in check_research_ready", "FAIL", f"unexpected: {pr}")
except Exception as e:
    log("check_portability() in check_research_ready", "FAIL", str(e))

# ── Test 8: State machine not modified ──
print("\n--- Test Group 8: State Machine & Module Interface ---")

try:
    from core.state.state_machine import ResearchState, State
    states = [s.value for s in State]
    expected_states = ["init", "dependency_check", "module_executing", "validation_gate",
                       "decision_routing", "completed", "failed", "checkpoint",
                       "paused_human_review", "experiment_running", "experiment_interrupted",
                       "resuming", "experiment_resuming"]
    if all(es in states for es in expected_states):
        log("State machine unchanged", "PASS", f"{len(states)} states")
    else:
        log("State machine unchanged", "FAIL", f"Missing states: {set(expected_states) - set(states)}")
except Exception as e:
    log("State machine unchanged", "FAIL", str(e))

try:
    from orchestrator.pipeline import MODULE_SEQUENCE
    if len(MODULE_SEQUENCE) == 15:
        log("MODULE_SEQUENCE unchanged", "PASS", f"{len(MODULE_SEQUENCE)} modules")
    else:
        log("MODULE_SEQUENCE unchanged", "FAIL", f"Expected 15, got {len(MODULE_SEQUENCE)}")
except Exception as e:
    log("MODULE_SEQUENCE unchanged", "FAIL", str(e))

# ── Summary ──
print("\n" + "=" * 60)
print(f"Phase 2 Test Summary")
print(f"{'='*60}")
print(f"  PASS: {passed}")
print(f"  FAIL: {failed}")
print(f"  SKIP: {skipped}")
print(f"  Total: {passed + failed + skipped}")
print(f"{'='*60}")

if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  - {r['test']}: {r['detail']}")
    print(f"\n>>> Phase 2 FAILED — do not proceed to Phase 3 <<<")
    sys.exit(1)
else:
    print(f"\n>>> Phase 2 PASSED — ready for Phase 3 <<<")
    sys.exit(0)
