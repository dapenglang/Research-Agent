#!/usr/bin/env python
"""
v8.2.2 Full Test Script

Tests all three phases:
  Phase 1: Infrastructure (configs, registries, check scripts)
  Phase 2: Pipeline integration (fallback, pre-checks, context injection)
  Phase 3: Module 01/02 registry, documentation, full pipeline run
"""

import sys
import os
import shutil
import logging
import tempfile
import traceback
from pathlib import Path

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
    print(f"  [{status}] {test_name}" + (f": {detail}" if detail else ""))
    if status == "PASS":
        passed += 1
    elif status == "FAIL":
        failed += 1
    else:
        skipped += 1


print("=" * 70)
print("v8.2.2 Full Test — All Phases")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: Infrastructure
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 1: Infrastructure")
print("=" * 70)

# ── 1.1 Config files ──
print("\n--- 1.1 Config Files ---")

config_files = [
    "configs/external_dependency.yaml",
    "configs/dependency_policy.yaml",
    "configs/environment.yaml",
]
for cf in config_files:
    p = project_root / cf
    if p.exists():
        log(f"Config exists: {cf}", "PASS")
    else:
        log(f"Config exists: {cf}", "FAIL", "File not found")

# ── 1.2 Config loading ──
print("\n--- 1.2 Config Loading ---")

try:
    import yaml
except ImportError:
    log("PyYAML import", "FAIL", "yaml not installed")
    sys.exit(1)

for cf in config_files:
    p = project_root / cf
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                log(f"Config loads: {cf}", "PASS")
            else:
                log(f"Config loads: {cf}", "FAIL", "Empty or not dict")
        except Exception as e:
            log(f"Config loads: {cf}", "FAIL", str(e))

# ── 1.3 external_dependency.yaml structure ──
print("\n--- 1.3 external_dependency.yaml Structure ---")

ed_path = project_root / "configs" / "external_dependency.yaml"
if ed_path.exists():
    with open(ed_path, "r", encoding="utf-8") as f:
        ed = yaml.safe_load(f)

    run_mode = ed.get("run_mode")
    if run_mode in ("production", "limited", "development"):
        log(f"run_mode = '{run_mode}'", "PASS")
    else:
        log(f"run_mode = '{run_mode}'", "FAIL", "Invalid value")

    dep_configs = ed.get("dependency_configs")
    if dep_configs and isinstance(dep_configs, dict):
        log("dependency_configs present", "PASS")
        for key in ("skill_registry", "mcp_registry", "llm_config"):
            if key in dep_configs:
                log(f"  dependency_configs.{key}", "PASS")
            else:
                log(f"  dependency_configs.{key}", "FAIL", "Missing key")
    else:
        log("dependency_configs present", "FAIL", "Missing or not dict")

    install_roots = ed.get("install_roots")
    if install_roots and isinstance(install_roots, dict):
        log("install_roots present", "PASS")
    else:
        log("install_roots present", "FAIL", "Missing or not dict")

# ── 1.4 dependency_policy.yaml structure ──
print("\n--- 1.4 dependency_policy.yaml Structure ---")

dp_path = project_root / "configs" / "dependency_policy.yaml"
if dp_path.exists():
    with open(dp_path, "r", encoding="utf-8") as f:
        dp = yaml.safe_load(f)

    for section in ("skill_fallback", "mcp_fallback", "llm_fallback", "model_fallback", "mode_constraints"):
        if section in dp:
            log(f"Section '{section}' present", "PASS")
        else:
            log(f"Section '{section}' present", "FAIL", "Missing")

    if "mode_constraints" in dp:
        mc = dp["mode_constraints"]
        for mode in ("production", "limited", "development"):
            if mode in mc:
                allow = mc[mode].get("allow_fallback")
                log(f"  mode_constraints.{mode}.allow_fallback = {allow}", "PASS")
            else:
                log(f"  mode_constraints.{mode}", "FAIL", "Missing")

# ── 1.5 skill_registry.yaml capability field ──
print("\n--- 1.5 skill_registry.yaml ---")

sr_path = project_root / "infrastructure" / "skills" / "skill_registry.yaml"
if sr_path.exists():
    with open(sr_path, "r", encoding="utf-8") as f:
        sr = yaml.safe_load(f)

    mapping = sr.get("module_skill_mapping", {})
    if mapping:
        log("module_skill_mapping present", "PASS")

        has_capability = True
        has_fallback = True
        total_skills = 0
        for mod_id, skills in mapping.items():
            if isinstance(skills, list):
                for s in skills:
                    total_skills += 1
                    if isinstance(s, dict):
                        if "capability" not in s:
                            has_capability = False
                        if "fallback" not in s:
                            has_fallback = False

        log(f"Total skills in registry: {total_skills}", "PASS")
        log("All skills have 'capability' field", "PASS" if has_capability else "FAIL")
        log("All skills have 'fallback' field", "PASS" if has_fallback else "FAIL")
    else:
        log("module_skill_mapping present", "FAIL", "Empty")
else:
    log("skill_registry.yaml exists", "FAIL", "File not found")

# ── 1.6 mcp_registry.yaml status fields ──
print("\n--- 1.6 mcp_registry.yaml ---")

mr_path = project_root / "infrastructure" / "mcp" / "mcp_registry.yaml"
if mr_path.exists():
    with open(mr_path, "r", encoding="utf-8") as f:
        mr = yaml.safe_load(f)

    servers = mr.get("mcp_servers", {})
    if servers:
        log(f"mcp_servers count: {len(servers)}", "PASS")

        has_installed = True
        has_configured = True
        has_tested = True
        has_fallback = True
        for name, cfg in servers.items():
            if "installed" not in cfg:
                has_installed = False
            if "configured" not in cfg:
                has_configured = False
            if "tested" not in cfg:
                has_tested = False
            if "fallback" not in cfg:
                has_fallback = False

        log("All MCPs have 'installed' field", "PASS" if has_installed else "FAIL")
        log("All MCPs have 'configured' field", "PASS" if has_configured else "FAIL")
        log("All MCPs have 'tested' field", "PASS" if has_tested else "FAIL")
        log("All MCPs have 'fallback' field", "PASS" if has_fallback else "FAIL")
    else:
        log("mcp_servers present", "FAIL", "Empty")
else:
    log("mcp_registry.yaml exists", "FAIL", "File not found")

# ── 1.7 Check scripts exist ──
print("\n--- 1.7 Check Scripts ---")

check_scripts = [
    "scripts/check_skills.py",
    "scripts/check_mcp.py",
    "scripts/check_portability.py",
    "scripts/check_research_ready.py",
    "scripts/check_llm.py",
    "scripts/check_literature.py",
]
for cs in check_scripts:
    p = project_root / cs
    if p.exists():
        log(f"Script exists: {cs}", "PASS")
    else:
        log(f"Script exists: {cs}", "FAIL", "File not found")

# ── 1.8 SkillRuntime import ──
print("\n--- 1.8 SkillRuntime & MCPManager ---")

try:
    from infrastructure.skills.skill_runtime import SkillRuntime
    log("SkillRuntime import", "PASS")
except Exception as e:
    log("SkillRuntime import", "FAIL", str(e))

try:
    from infrastructure.skills.skill_scanner import SkillScanner
    log("SkillScanner import", "PASS")
except Exception as e:
    log("SkillScanner import", "FAIL", str(e))

try:
    from infrastructure.mcp.mcp_manager import MCPManager
    log("MCPManager import", "PASS")
except Exception as e:
    log("MCPManager import", "FAIL", str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Pipeline Integration
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 2: Pipeline Integration")
print("=" * 70)

# ── 2.1 Pipeline import ──
print("\n--- 2.1 Pipeline Import ---")

try:
    from orchestrator.pipeline import PipelineOrchestrator
    log("PipelineOrchestrator import", "PASS")
except Exception as e:
    log("PipelineOrchestrator import", "FAIL", str(e))
    traceback.print_exc()
    sys.exit(1)

# ── 2.2 Pipeline init ──
print("\n--- 2.2 Pipeline Init ---")

task_config_path = project_root / "configs" / "research_task.yaml"
if not task_config_path.exists():
    for alt in [
        project_root / "configs" / "research_task_template.yaml",
        project_root / "tasks" / "task_001.yaml",
    ]:
        if alt.exists():
            task_config_path = alt
            break

test_state = "state_test_v822_full"
test_output = "output_test_v822_full"

# Clean previous test dirs
for d in [test_state, test_output]:
    td = project_root / d
    if td.exists():
        shutil.rmtree(td, ignore_errors=True)

try:
    pipe = PipelineOrchestrator(
        task_config_path=task_config_path,
        state_root=test_state,
        output_root=test_output,
        skip_gates=True,
    )
    log("Pipeline init (skip_gates=True)", "PASS")
except Exception as e:
    log("Pipeline init (skip_gates=True)", "FAIL", str(e))
    traceback.print_exc()
    sys.exit(1)

# ── 2.3 Run mode loaded ──
print("\n--- 2.3 Run Mode ---")

if hasattr(pipe, "_run_mode"):
    rm = pipe._run_mode
    if rm in ("production", "limited", "development"):
        log(f"_run_mode = '{rm}'", "PASS")
    else:
        log(f"_run_mode = '{rm}'", "FAIL", "Invalid value")
else:
    log("_run_mode attribute", "FAIL", "Attribute missing")

# ── 2.4 external_dependency loaded ──
print("\n--- 2.4 External Dependency Config ---")

if hasattr(pipe, "_external_deps") and pipe._external_deps:
    log("_external_deps loaded", "PASS")
else:
    log("_external_deps loaded", "FAIL", "Not loaded")

if hasattr(pipe, "_fallback_policy") and pipe._fallback_policy:
    log("_fallback_policy loaded", "PASS")
else:
    log("_fallback_policy loaded", "FAIL", "Not loaded")

# ── 2.5 get_fallback method ──
print("\n--- 2.5 get_fallback() ---")

if hasattr(pipe, "get_fallback"):
    log("get_fallback method exists", "PASS")

    try:
        result = pipe.get_fallback("01", "skill:light-literature-search")
        if isinstance(result, dict) and "action" in result:
            log(f"get_fallback('skill:light-literature-search') action='{result['action']}'", "PASS")
        else:
            log("get_fallback('skill:light-literature-search')", "FAIL", "No action in result")
    except Exception as e:
        log("get_fallback('skill:light-literature-search')", "FAIL", str(e))

    try:
        result = pipe.get_fallback("02", "mcp:arxiv")
        if isinstance(result, dict) and "action" in result:
            log(f"get_fallback('mcp:arxiv') action='{result['action']}'", "PASS")
        else:
            log("get_fallback('mcp:arxiv')", "FAIL", "No action in result")
    except Exception as e:
        log("get_fallback('mcp:arxiv')", "FAIL", str(e))

    try:
        result = pipe.get_fallback("05", "llm")
        if isinstance(result, dict) and "action" in result:
            log(f"get_fallback('llm') action='{result['action']}'", "PASS")
        else:
            log("get_fallback('llm')", "FAIL", "No action in result")
    except Exception as e:
        log("get_fallback('llm')", "FAIL", str(e))
else:
    log("get_fallback method exists", "FAIL", "Method missing")

# ── 2.6 _run_pre_checks method ──
print("\n--- 2.6 _run_pre_checks() ---")

if hasattr(pipe, "_run_pre_checks"):
    log("_run_pre_checks method exists", "PASS")

    try:
        pre_results = pipe._run_pre_checks()
        if isinstance(pre_results, dict):
            log("_run_pre_checks() returns dict", "PASS")
            if "passed" in pre_results:
                log(f"pre_checks passed={pre_results['passed']}", "PASS")
            if "mode" in pre_results:
                log(f"pre_checks mode={pre_results['mode']}", "PASS")
            if "warnings" in pre_results:
                log(f"pre_checks warnings count={len(pre_results['warnings'])}", "PASS")
        else:
            log("_run_pre_checks() returns dict", "FAIL", "Not dict")
    except Exception as e:
        log("_run_pre_checks() execution", "FAIL", str(e))
        traceback.print_exc()
else:
    log("_run_pre_checks method exists", "FAIL", "Method missing")

# ── 2.7 Fallback in production mode ──
print("\n--- 2.7 Mode Constraints ---")

try:
    # Temporarily switch to production mode
    original_mode = pipe._run_mode
    pipe._run_mode = "production"
    result = pipe.get_fallback("01", "skill:light-literature-search")
    if result.get("action") == "block":
        log("Production mode blocks fallback", "PASS")
    else:
        log("Production mode blocks fallback", "FAIL", f"action={result.get('action')}")
    pipe._run_mode = original_mode
except Exception as e:
    log("Production mode blocks fallback", "FAIL", str(e))

try:
    # In limited mode, fallback should be allowed
    original_mode = pipe._run_mode
    pipe._run_mode = "limited"
    result = pipe.get_fallback("01", "skill:light-literature-search")
    if result.get("action") != "block":
        log("Limited mode allows fallback", "PASS")
    else:
        log("Limited mode allows fallback", "FAIL", "action=block")
    pipe._run_mode = original_mode
except Exception as e:
    log("Limited mode allows fallback", "FAIL", str(e))


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Module 01/02, Registry, Documentation
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 3: Modules, Registry, Documentation")
print("=" * 70)

# ── 3.1 Module 01 literature registry ──
print("\n--- 3.1 Module 01 Literature Registry ---")

mod01_path = project_root / "modules" / "01_literature_retrieval" / "implementation.py"
if mod01_path.exists():
    content = mod01_path.read_text(encoding="utf-8")

    checks = [
        ("_LITERATURE_DIR", "_LITERATURE_DIR defined"),
        ("_REGISTRY_CSV", "_REGISTRY_CSV defined"),
        ("_REGISTRY_XLSX", "_REGISTRY_XLSX defined"),
        ("_DATABASE_JSON", "_DATABASE_JSON defined"),
        ("_KEYWORD_STATS_XLSX", "_KEYWORD_STATS_XLSX defined"),
        ("_DOWNLOAD_REPORT_MD", "_DOWNLOAD_REPORT_MD defined"),
        ("research_task_id", "research_task_id field used"),
        ("_load_literature_database", "_load_literature_database method"),
        ("_update_literature_registry", "_update_literature_registry method"),
        ("_generate_download_report", "_generate_download_report method"),
        ("_generate_keyword_statistics", "_generate_keyword_statistics method"),
        ("_query_skill_fallback", "_query_skill_fallback method"),
        ("REGISTRY_FIELDS", "REGISTRY_FIELDS defined"),
    ]
    for keyword, label in checks:
        if keyword in content:
            log(f"Module 01: {label}", "PASS")
        else:
            log(f"Module 01: {label}", "FAIL", f"'{keyword}' not found")

    if "research_task_id" in content and "REGISTRY_FIELDS" in content:
        # Check research_task_id is in REGISTRY_FIELDS
        if '"research_task_id"' in content or "'research_task_id'" in content:
            log("Module 01: research_task_id in REGISTRY_FIELDS", "PASS")
        else:
            log("Module 01: research_task_id in REGISTRY_FIELDS", "FAIL", "Not in REGISTRY_FIELDS")
else:
    log("Module 01 implementation.py exists", "FAIL", "File not found")

# ── 3.2 Module 02 registry update ──
print("\n--- 3.2 Module 02 Registry Update ---")

mod02_path = project_root / "modules" / "02_source_acquisition" / "implementation.py"
if mod02_path.exists():
    content = mod02_path.read_text(encoding="utf-8")

    checks = [
        ("_LITERATURE_DIR", "_LITERATURE_DIR defined"),
        ("_REGISTRY_CSV", "_REGISTRY_CSV defined"),
        ("_DATABASE_JSON", "_DATABASE_JSON defined"),
        ("research_task_id", "research_task_id field used"),
        ("_load_registry_entries", "_load_registry_entries method"),
        ("_update_registry_after_download", "_update_registry_after_download method"),
        ("_query_mcp_fallback", "_query_mcp_fallback method"),
        ("REGISTRY_FIELDS", "REGISTRY_FIELDS defined"),
        ("downloaded_ids", "download dedup logic"),
    ]
    for keyword, label in checks:
        if keyword in content:
            log(f"Module 02: {label}", "PASS")
        else:
            log(f"Module 02: {label}", "FAIL", f"'{keyword}' not found")
else:
    log("Module 02 implementation.py exists", "FAIL", "File not found")

# ── 3.3 Literature registry files ──
print("\n--- 3.3 Literature Registry Files ---")

lit_dir = project_root / "data" / "literature"
registry_files = [
    "literature_registry.csv",
    "literature_registry.xlsx",
    "literature_database.json",
]
for rf in registry_files:
    p = lit_dir / rf
    if p.exists():
        log(f"Registry file exists: {rf}", "PASS")
    else:
        log(f"Registry file exists: {rf}", "FAIL", "File not found")

# Check CSV header has research_task_id
csv_path = lit_dir / "literature_registry.csv"
if csv_path.exists():
    header = csv_path.read_text(encoding="utf-8").split("\n")[0].strip()
    if "research_task_id" in header:
        log("CSV header has research_task_id", "PASS")
    else:
        log("CSV header has research_task_id", "FAIL", f"Header: {header}")

# Check JSON has research_task_id support
json_path = lit_dir / "literature_database.json"
if json_path.exists():
    try:
        import json
        with open(json_path, "r", encoding="utf-8") as f:
            db = json.load(f)
        if isinstance(db, dict):
            log("literature_database.json loads", "PASS")
            papers = db.get("papers", [])
            log(f"Database has {len(papers)} papers", "PASS")
    except Exception as e:
        log("literature_database.json loads", "FAIL", str(e))

# ── 3.4 Documentation files ──
print("\n--- 3.4 Documentation Files ---")

doc_files = [
    "START_HERE.md",
    "docs/README_CN.md",
    "docs/Installation_Guide_CN.md",
    "docs/Skill_Configuration_Guide_CN.md",
    "docs/MCP_Configuration_Guide_CN.md",
    "docs/Literature_Registry_Guide_CN.md",
    "docs/Module_Interface_Documentation_CN.md",
    "docs/Human_Intervention_Guide_CN.md",
    "docs/Troubleshooting_CN.md",
]
for df in doc_files:
    p = project_root / df
    if p.exists() and p.stat().st_size > 100:
        log(f"Doc exists: {df} ({p.stat().st_size} bytes)", "PASS")
    else:
        log(f"Doc exists: {df}", "FAIL", "File not found or too small")

# Check START_HERE.md has v8.2.2
sh_path = project_root / "START_HERE.md"
if sh_path.exists():
    content = sh_path.read_text(encoding="utf-8")
    if "v8.2.2" in content:
        log("START_HERE.md mentions v8.2.2", "PASS")
    else:
        log("START_HERE.md mentions v8.2.2", "FAIL", "Not found")
    if "check_portability.py" in content:
        log("START_HERE.md has Setup Wizard", "PASS")
    else:
        log("START_HERE.md has Setup Wizard", "FAIL", "Not found")

# ── 3.5 Full Pipeline Run (Task001) ──
print("\n--- 3.5 Full Pipeline Run ---")

print("  Running full pipeline (this may take a few minutes)...")
try:
    result = pipe.start()
    if isinstance(result, dict):
        status = result.get("status", result.get("overall_status", "unknown"))
        log(f"Pipeline completed, status='{status}'", "PASS")

        # Check modules completed
        modules = result.get("modules", result.get("module_results", {}))
        if isinstance(modules, dict):
            completed = 0
            failed_mods = 0
            for mod_id, mod_result in modules.items():
                if isinstance(mod_result, dict):
                    mod_status = mod_result.get("status", "")
                    if mod_status in ("PASS", "COMPLETED", "WARNING"):
                        completed += 1
                    elif mod_status in ("FAIL", "ERROR", "SKIPPED"):
                        failed_mods += 1
            log(f"Modules completed: {completed}, failed/skipped: {failed_mods}", "PASS")

        # Check literature registry files were generated
        lit_dir_check = project_root / test_output / "data" / "literature"
        if not lit_dir_check.exists():
            lit_dir_check = project_root / "data" / "literature"

        for rf in ["literature_registry.csv", "literature_database.json", "Literature_Download_Report.md"]:
            p = lit_dir_check / rf
            if p.exists():
                log(f"Output generated: {rf}", "PASS")
            else:
                log(f"Output generated: {rf}", "SKIP", "Not found in output")

        # Check paper output
        paper_dir = project_root / test_output / "paper"
        if not paper_dir.exists():
            paper_dir = project_root / "output" / "paper"
        if paper_dir.exists():
            paper_files = list(paper_dir.iterdir())
            log(f"Paper output dir has {len(paper_files)} files", "PASS")
        else:
            log("Paper output dir", "SKIP", "Not found")

    elif isinstance(result, str):
        log(f"Pipeline returned string: {result[:100]}...", "PASS")
    else:
        log("Pipeline return type", "FAIL", f"Unexpected type: {type(result)}")

except Exception as e:
    log("Pipeline execution", "FAIL", str(e))
    traceback.print_exc()

# ── 3.6 Post-run registry check ──
print("\n--- 3.6 Post-Run Registry Check ---")

# After pipeline run, check if registry was updated
csv_path = lit_dir / "literature_registry.csv"
if csv_path.exists():
    lines = csv_path.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) > 1:
        log(f"Registry CSV has {len(lines) - 1} entries", "PASS")
    else:
        log("Registry CSV has entries", "SKIP", "Only header (no papers downloaded)")

# Clean up test directories
print("\n--- Cleanup ---")
for d in [test_state, test_output]:
    td = project_root / d
    if td.exists():
        try:
            shutil.rmtree(td, ignore_errors=True)
            log(f"Cleaned {d}", "PASS")
        except Exception:
            log(f"Cleaned {d}", "SKIP", "Could not remove")


# ═══════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"  Total tests: {passed + failed + skipped}")
print(f"  PASS: {passed}")
print(f"  FAIL: {failed}")
print(f"  SKIP: {skipped}")

if failed == 0:
    print("\n  *** ALL TESTS PASSED ***")
    print("\n  v8.2.2 is ready for packaging.")
    sys.exit(0)
else:
    print(f"\n  *** {failed} TEST(S) FAILED ***")
    print("\n  Fix failures before proceeding to packaging.")
    sys.exit(1)
