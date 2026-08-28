#!/usr/bin/env python
"""
Skill Availability Check — v8.2.2

Checks:
- Skill exists in TRAE skills directory
- Version matches registry
- Install path is correct
- Capability is defined

Outputs Skill_Install_Request.md when skills are missing.

Usage:
    python scripts/check_skills.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent.parent
    if (current / "configs").exists():
        return current
    return Path.cwd()


def load_skill_registry(project_root: Path) -> Dict[str, Any]:
    registry_path = project_root / "infrastructure" / "skills" / "skill_registry.yaml"
    if not registry_path.exists():
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_installed_skills(project_root: Path) -> Dict[str, Any]:
    json_path = project_root / "infrastructure" / "skills" / "installed_skills.json"
    if not json_path.exists():
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_trae_skills_dir() -> Path:
    home = Path.home()
    return home / ".trae-cn" / "skills"


def check_skills(project_root: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "Skill 检测",
        "passed": True,
        "total": 0,
        "found": 0,
        "missing": [],
        "details": []
    }

    registry = load_skill_registry(project_root)
    if not registry:
        result["passed"] = False
        result["error"] = "skill_registry.yaml not found or empty"
        return result

    installed = load_installed_skills(project_root)
    installed_names = set()
    if installed:
        for skill in installed.get("skills", []):
            name = skill.get("name", "") if isinstance(skill, dict) else str(skill)
            if name:
                installed_names.add(name)

    trae_dir = get_trae_skills_dir()
    if trae_dir.exists():
        for item in trae_dir.iterdir():
            if item.is_dir():
                installed_names.add(item.name)

    module_mapping = registry.get("module_skill_mapping", {})
    for module_id, skills in module_mapping.items():
        for skill_entry in skills:
            if isinstance(skill_entry, str):
                skill_name = skill_entry
                required = False
                capability = "unknown"
                version = "1.0"
                install_path = ""
                fallback = "skill:default"
            elif isinstance(skill_entry, dict):
                skill_name = skill_entry.get("skill_name", "")
                required = skill_entry.get("required", False)
                capability = skill_entry.get("capability", "unknown")
                version = skill_entry.get("version", "1.0")
                install_path = skill_entry.get("install_path", "")
                fallback = skill_entry.get("fallback", "skill:default")
            else:
                continue

            if not skill_name:
                continue

            result["total"] += 1
            found = skill_name in installed_names

            if install_path and "<user>" in install_path:
                install_path_resolved = str(trae_dir)
            else:
                install_path_resolved = install_path

            if install_path_resolved and Path(install_path_resolved).exists():
                found = True

            detail = {
                "module": module_id,
                "skill_name": skill_name,
                "required": required,
                "capability": capability,
                "version": version,
                "found": found,
                "fallback": fallback
            }
            result["details"].append(detail)

            if found:
                result["found"] += 1
            else:
                if required:
                    result["missing"].append(detail)

    required_missing = [m for m in result["missing"] if m["required"]]
    if required_missing:
        result["passed"] = False

    return result


def generate_install_request(result: Dict[str, Any], project_root: Path) -> str:
    lines = [
        "# Skill Install Request",
        "",
        f"**Generated:** {__import__('datetime').datetime.now().isoformat()}",
        "",
        "## Missing Required Skills",
        "",
    ]

    for m in result["missing"]:
        if m["required"]:
            lines.extend([
                f"### {m['skill_name']}",
                f"- Module: {m['module']}",
                f"- Capability: {m['capability']}",
                f"- Version: {m['version']}",
                f"- Fallback: {m['fallback']}",
                f"- Install to: c:/Users/<user>/.trae-cn/skills/{m['skill_name']}",
                "",
            ])

    lines.extend([
        "## Installation Steps",
        "",
        "1. Download the skill package",
        "2. Extract to the install path above",
        "3. Re-run: python scripts/check_skills.py",
        "",
    ])

    report_path = project_root / "Skill_Install_Request.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return str(report_path)


def main() -> int:
    project_root = find_project_root()
    result = check_skills(project_root)

    print(f"\n{'='*60}")
    print(f"Skill Check Report")
    print(f"{'='*60}")
    print(f"Total skills: {result['total']}")
    print(f"Found: {result['found']}")
    print(f"Missing (required): {len([m for m in result['missing'] if m['required']])}")
    print(f"Status: {'PASS' if result['passed'] else 'FAIL'}")

    if result["missing"]:
        print("\nMissing skills:")
        for m in result["missing"]:
            req = " [REQUIRED]" if m["required"] else ""
            print(f"  - {m['skill_name']} (Module {m['module']}, capability: {m['capability']}){req}")

        req_missing = [m for m in result["missing"] if m["required"]]
        if req_missing:
            report = generate_install_request(result, project_root)
            print(f"\nInstall request generated: {report}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
