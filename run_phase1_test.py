#!/usr/bin/env python
"""
Phase 1 Test Script — v8.2.2 Infrastructure Upgrade

Tests:
1. SkillRuntime import and new methods
2. MCPManager import and new methods
3. Config file loading (external_dependency.yaml, dependency_policy.yaml)
4. Check scripts (check_skills.py, check_mcp.py, check_portability.py)
5. Backward compatibility (existing methods still work)
"""

import sys
import os
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

passed = 0
failed = 0
skipped = 0
results = []


def log(test_name, status, detail=""):
    global passed, failed, skipped
    emoji = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}
    results.append({"test": test_name, "status": status, "detail": detail})
    print(f"  [{emoji.get(status, status)}] {test_name}: {detail}" if detail else f"  [{emoji.get(status, status)}] {test_name}")
    if status == "PASS":
        passed += 1
    elif status == "FAIL":
        failed += 1
    else:
        skipped += 1


print("=" * 60)
print("Phase 1 Test: Infrastructure Upgrade v8.2.2")
print("=" * 60)

# ── Test 1: Config files exist ──
print("\n--- Test Group 1: Config Files ---")

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

# ── Test 2: Config files load correctly ──
print("\n--- Test Group 2: Config Loading ---")
import yaml

try:
    with open(project_root / "configs/external_dependency.yaml", "r", encoding="utf-8") as f:
        ext_dep = yaml.safe_load(f)
    if ext_dep and "run_mode" in ext_dep:
        log("external_dependency.yaml loads", "PASS", f"run_mode={ext_dep.get('run_mode')}")
    else:
        log("external_dependency.yaml loads", "FAIL", "Missing run_mode field")
except Exception as e:
    log("external_dependency.yaml loads", "FAIL", str(e))

try:
    with open(project_root / "configs/dependency_policy.yaml", "r", encoding="utf-8") as f:
        dep_policy = yaml.safe_load(f)
    if dep_policy and "skill_fallback" in dep_policy and "mcp_fallback" in dep_policy:
        log("dependency_policy.yaml loads", "PASS", f"skill_fallback keys={len(dep_policy.get('skill_fallback', {}))}")
    else:
        log("dependency_policy.yaml loads", "FAIL", "Missing skill_fallback or mcp_fallback")
except Exception as e:
    log("dependency_policy.yaml loads", "FAIL", str(e))

try:
    with open(project_root / "configs/environment.yaml", "r", encoding="utf-8") as f:
        env_cfg = yaml.safe_load(f)
    if env_cfg and "python" in env_cfg:
        log("environment.yaml loads", "PASS", f"python={env_cfg.get('python', {}).get('version', '?')}")
    else:
        log("environment.yaml loads", "FAIL", "Missing python field")
except Exception as e:
    log("environment.yaml loads", "FAIL", str(e))

# ── Test 3: SkillRuntime ──
print("\n--- Test Group 3: SkillRuntime ---")

try:
    from infrastructure.skills.skill_runtime import SkillRuntime
    sr = SkillRuntime()
    log("SkillRuntime import", "PASS")
except Exception as e:
    log("SkillRuntime import", "FAIL", str(e))
    sr = None

if sr:
    # Test registry loading
    try:
        reg = sr.registry
        if reg and "module_skill_mapping" in reg:
            module_count = len(reg.get("module_skill_mapping", {}))
            log("SkillRuntime.registry loads", "PASS", f"{module_count} modules")
        else:
            log("SkillRuntime.registry loads", "FAIL", "No module_skill_mapping")
    except Exception as e:
        log("SkillRuntime.registry loads", "FAIL", str(e))

    # Test check_skill_availability
    try:
        avail = sr.check_skill_availability("light-literature-search")
        required_fields = ["skill_name", "found", "version_match", "capability_defined", "required", "capability", "fallback_key", "issues"]
        all_present = all(k in avail for k in required_fields)
        if all_present:
            log("check_skill_availability()", "PASS", f"found={avail['found']}, capability={avail['capability']}, fallback_key={avail['fallback_key']}")
        else:
            log("check_skill_availability()", "FAIL", f"Missing fields: {set(required_fields) - set(avail.keys())}")
    except Exception as e:
        log("check_skill_availability()", "FAIL", str(e))

    # Test get_skill_capability
    try:
        cap = sr.get_skill_capability("light-literature-search")
        if cap and cap != "unknown":
            log("get_skill_capability()", "PASS", f"capability={cap}")
        else:
            log("get_skill_capability()", "WARN", f"capability={cap}")
    except Exception as e:
        log("get_skill_capability()", "FAIL", str(e))

    # Test get_skill_fallback_key
    try:
        fb = sr.get_skill_fallback_key("light-literature-search")
        if fb and fb.startswith("skill:"):
            log("get_skill_fallback_key()", "PASS", f"key={fb}")
        else:
            log("get_skill_fallback_key()", "FAIL", f"Unexpected key: {fb}")
    except Exception as e:
        log("get_skill_fallback_key()", "FAIL", str(e))

    # Test get_module_skill_details
    try:
        details = sr.get_module_skill_details("01")
        if details and len(details) > 0:
            first = details[0]
            if "skill_name" in first and "found" in first and "capability" in first:
                log("get_module_skill_details()", "PASS", f"{len(details)} skills for module 01")
            else:
                log("get_module_skill_details()", "FAIL", "Missing fields in detail")
        else:
            log("get_module_skill_details()", "FAIL", "No details returned")
    except Exception as e:
        log("get_module_skill_details()", "FAIL", str(e))

    # Test check_module_skills
    try:
        ms = sr.check_module_skills("01")
        if "all_required_present" in ms and "required_missing" in ms:
            log("check_module_skills()", "PASS", f"total={ms['total']}, found={ms['found']}, required_missing={len(ms['required_missing'])}")
        else:
            log("check_module_skills()", "FAIL", "Missing fields")
    except Exception as e:
        log("check_module_skills()", "FAIL", str(e))

    # Test check_all_modules
    try:
        am = sr.check_all_modules()
        if "modules" in am and "total_required_missing" in am:
            log("check_all_modules()", "PASS", f"modules={am['total_modules']}, required_missing={am['total_required_missing']}")
        else:
            log("check_all_modules()", "FAIL", "Missing fields")
    except Exception as e:
        log("check_all_modules()", "FAIL", str(e))

    # Backward compatibility: existing methods still work
    try:
        count = sr.get_total_count()
        log("Backward compat: get_total_count()", "PASS", f"{count} skills")
    except Exception as e:
        log("Backward compat: get_total_count()", "FAIL", str(e))

    try:
        prompt = sr.build_skill_prompt("01")
        log("Backward compat: build_skill_prompt()", "PASS", f"prompt length={len(prompt)}")
    except Exception as e:
        log("Backward compat: build_skill_prompt()", "FAIL", str(e))

    try:
        is_inst = sr.is_installed("light-literature-search")
        log("Backward compat: is_installed()", "PASS", f"installed={is_inst}")
    except Exception as e:
        log("Backward compat: is_installed()", "FAIL", str(e))

    # Verify NO fallback logic in SkillRuntime
    try:
        has_fallback_method = hasattr(sr, "execute_fallback") or hasattr(sr, "get_fallback")
        if not has_fallback_method:
            log("No fallback logic in SkillRuntime", "PASS", "Correctly delegates to Pipeline")
        else:
            log("No fallback logic in SkillRuntime", "FAIL", "Found fallback method — should not exist")
    except Exception as e:
        log("No fallback logic in SkillRuntime", "FAIL", str(e))

# ── Test 4: MCPManager ──
print("\n--- Test Group 4: MCPManager ---")

try:
    from infrastructure.mcp.mcp_manager import MCPManager
    mm = MCPManager()
    log("MCPManager import", "PASS")
except Exception as e:
    log("MCPManager import", "FAIL", str(e))
    mm = None

if mm:
    # Test servers loading
    try:
        servers = mm.servers
        if servers and len(servers) > 0:
            log("MCPManager.servers loads", "PASS", f"{len(servers)} servers")
        else:
            log("MCPManager.servers loads", "FAIL", "No servers")
    except Exception as e:
        log("MCPManager.servers loads", "FAIL", str(e))

    # Test check_availability
    try:
        avail = mm.check_availability("arxiv")
        required_fields = ["name", "enabled", "installed", "configured", "tested", "fallback_key", "issues"]
        all_present = all(k in avail for k in required_fields)
        if all_present:
            log("check_availability()", "PASS", f"installed={avail['installed']}, configured={avail['configured']}, tested={avail['tested']}")
        else:
            log("check_availability()", "FAIL", f"Missing fields: {set(required_fields) - set(avail.keys())}")
    except Exception as e:
        log("check_availability()", "FAIL", str(e))

    # Test check_all_availability
    try:
        all_avail = mm.check_all_availability()
        if "servers" in all_avail and "all_installed" in all_avail:
            log("check_all_availability()", "PASS", f"installed={all_avail['installed_count']}/{all_avail['total_enabled']}")
        else:
            log("check_all_availability()", "FAIL", "Missing fields")
    except Exception as e:
        log("check_all_availability()", "FAIL", str(e))

    # Test get_mcp_fallback_key
    try:
        fb = mm.get_mcp_fallback_key("arxiv")
        if fb and fb.startswith("mcp:"):
            log("get_mcp_fallback_key()", "PASS", f"key={fb}")
        else:
            log("get_mcp_fallback_key()", "FAIL", f"Unexpected key: {fb}")
    except Exception as e:
        log("get_mcp_fallback_key()", "FAIL", str(e))

    # Test get_mcp_category
    try:
        cat = mm.get_mcp_category("arxiv")
        if cat and cat != "unknown":
            log("get_mcp_category()", "PASS", f"category={cat}")
        else:
            log("get_mcp_category()", "FAIL", f"category={cat}")
    except Exception as e:
        log("get_mcp_category()", "FAIL", str(e))

    # Backward compatibility
    try:
        avail = mm.is_available("arxiv")
        log("Backward compat: is_available()", "PASS", f"available={avail}")
    except Exception as e:
        log("Backward compat: is_available()", "FAIL", str(e))

    try:
        summary = mm.summary()
        log("Backward compat: summary()", "PASS", f"length={len(summary)}")
    except Exception as e:
        log("Backward compat: summary()", "FAIL", str(e))

    try:
        enabled = mm.list_enabled()
        log("Backward compat: list_enabled()", "PASS", f"{len(enabled)} enabled")
    except Exception as e:
        log("Backward compat: list_enabled()", "FAIL", str(e))

    # Verify NO fallback logic in MCPManager
    try:
        has_fallback_method = hasattr(mm, "execute_fallback") or hasattr(mm, "get_fallback")
        if not has_fallback_method:
            log("No fallback logic in MCPManager", "PASS", "Correctly delegates to Pipeline")
        else:
            log("No fallback logic in MCPManager", "FAIL", "Found fallback method — should not exist")
    except Exception as e:
        log("No fallback logic in MCPManager", "FAIL", str(e))

# ── Test 5: Check scripts ──
print("\n--- Test Group 5: Check Scripts ---")

try:
    sys.path.insert(0, str(project_root / "scripts"))
    from check_skills import check_skills as cs_func
    result = cs_func(project_root)
    if "passed" in result and "total" in result:
        log("check_skills.py", "PASS", f"total={result['total']}, found={result['found']}, passed={result['passed']}")
    else:
        log("check_skills.py", "FAIL", "Unexpected return format")
except Exception as e:
    log("check_skills.py", "FAIL", str(e))

try:
    from check_mcp import check_mcp as cm_func
    result = cm_func(project_root)
    if "passed" in result and "total" in result:
        log("check_mcp.py", "PASS", f"total={result['total']}, installed={result['installed_count']}, passed={result['passed']}")
    else:
        log("check_mcp.py", "FAIL", "Unexpected return format")
except Exception as e:
    log("check_mcp.py", "FAIL", str(e))

try:
    from check_portability import (
        check_python, check_conda, check_skills as cp_skills,
        check_mcp as cp_mcp, check_llm, check_gpu, check_storage,
        generate_install_order
    )
    checks = [
        check_python(),
        check_conda(),
        cp_skills(project_root),
        cp_mcp(project_root),
        check_llm(),
        check_gpu(),
        check_storage(project_root),
    ]
    order = generate_install_order(checks)
    log("check_portability.py", "PASS", f"{len(checks)} checks, install_order={len(order)} steps")
except Exception as e:
    log("check_portability.py", "FAIL", str(e))

# ── Test 6: skill_registry.yaml has capability field ──
print("\n--- Test Group 6: Config Field Validation ---")

try:
    with open(project_root / "infrastructure/skills/skill_registry.yaml", "r", encoding="utf-8") as f:
        sr_yaml = yaml.safe_load(f)
    mapping = sr_yaml.get("module_skill_mapping", {})
    has_capability = False
    has_fallback = False
    has_version = False
    has_required = False
    for skills in mapping.values():
        for s in skills:
            if isinstance(s, dict):
                if "capability" in s:
                    has_capability = True
                if "fallback" in s:
                    has_fallback = True
                if "version" in s:
                    has_version = True
                if "required" in s:
                    has_required = True
    if has_capability and has_fallback and has_version and has_required:
        log("skill_registry.yaml fields", "PASS", f"capability={has_capability}, fallback={has_fallback}, version={has_version}, required={has_required}")
    else:
        log("skill_registry.yaml fields", "FAIL", f"capability={has_capability}, fallback={has_fallback}, version={has_version}, required={has_required}")
except Exception as e:
    log("skill_registry.yaml fields", "FAIL", str(e))

try:
    with open(project_root / "infrastructure/mcp/mcp_registry.yaml", "r", encoding="utf-8") as f:
        mr_yaml = yaml.safe_load(f)
    servers = mr_yaml.get("mcp_servers", {})
    has_installed = False
    has_configured = False
    has_tested = False
    has_fallback = False
    for cfg in servers.values():
        if "installed" in cfg:
            has_installed = True
        if "configured" in cfg:
            has_configured = True
        if "tested" in cfg:
            has_tested = True
        if "fallback" in cfg:
            has_fallback = True
    if has_installed and has_configured and has_tested and has_fallback:
        log("mcp_registry.yaml fields", "PASS", f"installed={has_installed}, configured={has_configured}, tested={has_tested}, fallback={has_fallback}")
    else:
        log("mcp_registry.yaml fields", "FAIL", f"installed={has_installed}, configured={has_configured}, tested={has_tested}, fallback={has_fallback}")
except Exception as e:
    log("mcp_registry.yaml fields", "FAIL", str(e))

# ── Summary ──
print("\n" + "=" * 60)
print(f"Phase 1 Test Summary")
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
    print(f"\n>>> Phase 1 FAILED — do not proceed to Phase 2 <<<")
    sys.exit(1)
else:
    print(f"\n>>> Phase 1 PASSED — ready for Phase 2 <<<")
    sys.exit(0)
