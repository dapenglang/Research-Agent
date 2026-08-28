"""
Module Validator — validates that every module in the Research Agent v3
pipeline is structurally complete and importable.

Checks per module:
  1. Required files exist (interface.py, implementation.py, schema.py,
     validator.py, manifest.yaml, __main__.py, __init__.py)
  2. manifest.yaml is valid YAML with required fields
  3. implementation.py defines the expected implementation class
  4. The module can be imported without errors

Usage:
    python tools/module_validator.py                  # validate all modules
    python tools/module_validator.py --module 01       # validate a single module
    python tools/module_validator.py --json            # output as JSON
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODULES_DIR = _PROJECT_ROOT / "modules"

REQUIRED_FILES = [
    "__init__.py",
    "interface.py",
    "implementation.py",
    "schema.py",
    "validator.py",
    "manifest.yaml",
    "__main__.py",
]

REQUIRED_MANIFEST_FIELDS = [
    "module_id",
    "module_name",
    "module_version",
    "schema_version",
    "description",
    "dependencies",
    "inputs",
    "outputs",
    "status",
]

IMPL_CLASS_MAP = {
    "01": "LiteratureRetrievalImplementation",
    "02": "SourceAcquisitionImplementation",
    "02_5": "PaperAssetIntelligenceEngine",
    "03": "LiteratureIntelligenceImplementation",
    "04": "ResearchLandscapeModule",
    "05": "InnovationReasoningModule",
    "06": "TheoryMethodModule",
    "07": "ExperimentPlanningModule",
    "08": "SyntheticExperimentEngine",
    "09": "RealExperimentEngine",
    "10": "ResultAnalysisEngine",
    "11": "FigureTableEngine",
    "12": "PaperWritingEngine",
    "13": "ReferenceSupplementaryEngine",
}

MODULE_DIR_MAP = {
    "01": "01_literature_retrieval",
    "02": "02_source_acquisition",
    "02_5": "02_5_paper_asset_intelligence",
    "03": "03_literature_intelligence",
    "04": "04_research_landscape",
    "05": "05_innovation_reasoning",
    "06": "06_theory_method",
    "07": "07_experiment_planning",
    "08": "08_synthetic_experiment_engine",
    "09": "09_real_experiment_engine",
    "10": "10_result_analysis",
    "11": "11_figure_table",
    "12": "12_paper_writing",
    "13": "13_reference_supplementary",
}


def _check_files(module_dir: Path) -> List[Dict[str, Any]]:
    """Check that all required files exist in the module directory."""
    issues = []
    for fname in REQUIRED_FILES:
        fpath = module_dir / fname
        if not fpath.exists():
            issues.append({
                "check": "file_exists",
                "file": fname,
                "status": "FAIL",
                "message": f"Missing required file: {fname}",
            })
        elif fpath.stat().st_size == 0 and fname not in ("__init__.py",):
            issues.append({
                "check": "file_exists",
                "file": fname,
                "status": "WARN",
                "message": f"File is empty: {fname}",
            })
    return issues


def _check_manifest(module_dir: Path, module_id: str) -> List[Dict[str, Any]]:
    """Validate the manifest.yaml file."""
    issues = []
    manifest_path = module_dir / "manifest.yaml"
    if not manifest_path.exists():
        issues.append({
            "check": "manifest",
            "status": "FAIL",
            "message": "manifest.yaml not found",
        })
        return issues

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as e:
        issues.append({
            "check": "manifest",
            "status": "FAIL",
            "message": f"YAML parse error: {e}",
        })
        return issues

    if manifest is None:
        issues.append({
            "check": "manifest",
            "status": "FAIL",
            "message": "manifest.yaml is empty",
        })
        return issues

    if not isinstance(manifest, dict):
        issues.append({
            "check": "manifest",
            "status": "FAIL",
            "message": "manifest.yaml root is not a mapping",
        })
        return issues

    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            issues.append({
                "check": "manifest",
                "status": "FAIL",
                "message": f"Missing required field: {field}",
            })

    actual_id = manifest.get("module_id", "")
    if actual_id != module_id:
        issues.append({
            "check": "manifest",
            "status": "WARN",
            "message": f"module_id mismatch: expected '{module_id}', got '{actual_id}'",
        })

    status_block = manifest.get("status", {})
    if isinstance(status_block, dict):
        default_status = status_block.get("default", "")
        if default_status not in ("NOT_STARTED", "READY", "IN_PROGRESS", "COMPLETED", "FAILED"):
            issues.append({
                "check": "manifest",
                "status": "WARN",
                "message": f"Unusual default status: '{default_status}'",
            })

    return issues


def _check_import(module_dir: Path, module_id: str) -> List[Dict[str, Any]]:
    """Try to import the implementation module and verify the class exists.

    Replicates the pipeline's _load_module logic:
    - Evict cached bare-name modules (interface, schema, validator) so the
      correct local files are loaded for each module.
    - Set __package__ for modules 04-07 which use relative imports.
    """
    issues = []
    impl_path = module_dir / "implementation.py"
    if not impl_path.exists():
        issues.append({
            "check": "import",
            "status": "FAIL",
            "message": "implementation.py not found, cannot import",
        })
        return issues

    expected_class = IMPL_CLASS_MAP.get(module_id, "")
    if not expected_class:
        issues.append({
            "check": "import",
            "status": "WARN",
            "message": f"No expected class name registered for module {module_id}",
        })
        return issues

    module_name = f"_validate_mod_{module_id.replace('.', '_')}"
    module_dir_str = str(module_dir)
    v3_root_str = str(_PROJECT_ROOT)

    for p in (module_dir_str, v3_root_str):
        if p not in sys.path:
            sys.path.insert(0, p)

    # Evict cached bare-name modules so the correct local files are loaded
    for stale_key in ("interface", "schema", "validator"):
        sys.modules.pop(stale_key, None)

    # Modules 04-07 use relative imports; set __package__ for resolution
    dir_name = module_dir.name
    pkg_name = f"Research_Agent_v3.modules.{dir_name}"

    try:
        spec = importlib.util.spec_from_file_location(
            module_name,
            str(impl_path),
            submodule_search_locations=[module_dir_str],
        )
        if spec is None or spec.loader is None:
            issues.append({
                "check": "import",
                "status": "FAIL",
                "message": "Could not create import spec for implementation.py",
            })
            return issues

        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)

        if not hasattr(mod, expected_class):
            issues.append({
                "check": "import",
                "status": "FAIL",
                "message": f"Class '{expected_class}' not found in implementation.py",
            })
        else:
            cls = getattr(mod, expected_class)
            try:
                instance = cls()
                if hasattr(instance, "load_config"):
                    instance.load_config({
                        "output": {"paper_dir": "output/paper"},
                        "llm": {"type": "mock"},
                    })
            except Exception:
                pass

    except Exception as e:
        issues.append({
            "check": "import",
            "status": "FAIL",
            "message": f"Import error: {e}",
        })

    return issues


def validate_module(module_id: str) -> Dict[str, Any]:
    """Run all checks for a single module and return the result dict."""
    dir_name = MODULE_DIR_MAP.get(module_id, "")
    if not dir_name:
        return {
            "module_id": module_id,
            "status": "ERROR",
            "issues": [{"check": "config", "status": "FAIL", "message": f"Unknown module_id: {module_id}"}],
        }

    module_dir = _MODULES_DIR / dir_name
    if not module_dir.exists():
        return {
            "module_id": module_id,
            "module_dir": dir_name,
            "status": "ERROR",
            "issues": [{"check": "dir_exists", "status": "FAIL", "message": f"Module directory not found: {dir_name}"}],
        }

    all_issues: List[Dict[str, Any]] = []
    all_issues.extend(_check_files(module_dir))
    all_issues.extend(_check_manifest(module_dir, module_id))
    all_issues.extend(_check_import(module_dir, module_id))

    has_fail = any(i["status"] == "FAIL" for i in all_issues)
    status = "FAIL" if has_fail else "PASS"

    return {
        "module_id": module_id,
        "module_dir": dir_name,
        "status": status,
        "issues": all_issues,
    }


def validate_all() -> List[Dict[str, Any]]:
    """Validate all modules in sequence order."""
    results = []
    for mid in IMPL_CLASS_MAP:
        results.append(validate_module(mid))
    return results


def print_report(results: List[Dict[str, Any]]) -> bool:
    """Print a human-readable validation report. Returns True if all pass."""
    print("=" * 70)
    print("  Research Agent v3 — Module Validation Report")
    print("=" * 70)
    print()

    all_pass = True
    for r in results:
        status_str = r["status"]
        icon = "[PASS]" if status_str == "PASS" else "[FAIL]"
        if status_str != "PASS":
            all_pass = False
        print(f"  {icon} Module {r['module_id']:<5} — {r.get('module_dir', 'N/A')}")

        for issue in r.get("issues", []):
            lvl = issue["status"]
            icon2 = "  [FAIL]" if lvl == "FAIL" else "  [WARN]"
            print(f"         {icon2} {issue['message']}")

    print()
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed
    print(f"  Summary: {passed}/{total} modules passed, {failed} failed")
    print("=" * 70)
    return all_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Research Agent v3 modules")
    parser.add_argument("--module", type=str, default=None, help="Validate a single module by ID (e.g. 01, 02_5)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    if args.module:
        results = [validate_module(args.module)]
    else:
        results = validate_all()

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        all_pass = print_report(results)
        if not all_pass:
            sys.exit(1)


if __name__ == "__main__":
    main()
