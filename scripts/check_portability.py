#!/usr/bin/env python
"""
Portability Check — v8.2.2

Comprehensive migration detection for new machine deployment.
Checks: Python, Conda, Skills, MCP, LLM, Models, GPU, Storage.
Generates Migration_Check_Report.md with installation order.

Usage:
    python scripts/check_portability.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent.parent
    if (current / "configs").exists():
        return current
    return Path.cwd()


def check_python() -> Dict[str, Any]:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    passed = sys.version_info >= (3, 10)
    return {
        "name": "Python 环境",
        "status": "PASS" if passed else "FAIL",
        "details": {"version": version, "required": ">=3.10"},
        "passed": passed
    }


def check_conda() -> Dict[str, Any]:
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    passed = conda_env == "research_agent_v3"
    return {
        "name": "Conda 环境",
        "status": "PASS" if passed else "WARN",
        "details": {"current_env": conda_env or "(none)", "required": "research_agent_v3"},
        "passed": passed
    }


def check_skills(project_root: Path) -> Dict[str, Any]:
    registry_path = project_root / "infrastructure" / "skills" / "skill_registry.yaml"
    installed_json = project_root / "infrastructure" / "skills" / "installed_skills.json"

    if not registry_path.exists():
        return {"name": "Skill 安装", "status": "FAIL", "details": "registry not found", "passed": False}

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    installed_count = 0
    if installed_json.exists():
        with open(installed_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        installed_count = len(data.get("skills", []))

    total = 0
    required_missing = 0
    for module_id, skills in registry.get("module_skill_mapping", {}).items():
        for s in skills:
            if isinstance(s, dict):
                total += 1
                if s.get("required") and not s.get("install_path"):
                    required_missing += 1

    passed = required_missing == 0
    return {
        "name": "Skill 安装",
        "status": "PASS" if passed else "WARN",
        "details": {"installed": installed_count, "registry_entries": total, "required_missing": required_missing},
        "passed": passed
    }


def check_mcp(project_root: Path) -> Dict[str, Any]:
    registry_path = project_root / "infrastructure" / "mcp" / "mcp_registry.yaml"
    if not registry_path.exists():
        return {"name": "MCP 安装", "status": "FAIL", "details": "registry not found", "passed": False}

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    servers = registry.get("mcp_servers", {})
    enabled = {k: v for k, v in servers.items() if v.get("enabled")}
    installed = sum(1 for v in enabled.values() if v.get("installed"))
    not_installed = [k for k, v in enabled.items() if not v.get("installed")]

    passed = len(not_installed) == 0
    return {
        "name": "MCP 安装",
        "status": "PASS" if passed else "WARN",
        "details": {"enabled": len(enabled), "installed": installed, "not_installed": not_installed},
        "passed": passed
    }


def check_llm() -> Dict[str, Any]:
    openai_key = bool(os.environ.get("OPENAI_API_KEY"))
    deepseek_key = bool(os.environ.get("DEEPSEEK_API_KEY"))
    has_key = openai_key or deepseek_key

    return {
        "name": "LLM 配置",
        "status": "PASS" if has_key else "WARN",
        "details": {
            "openai": "configured" if openai_key else "not set",
            "deepseek": "configured" if deepseek_key else "not set"
        },
        "passed": True
    }


def check_models(project_root: Path) -> Dict[str, Any]:
    model_registry_path = project_root / "configs" / "model_registry.yaml"
    if not model_registry_path.exists():
        return {"name": "模型路径", "status": "WARN", "details": "registry not found", "passed": True}

    with open(model_registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    models = registry.get("models", {})
    found = 0
    missing = []
    for name, config in models.items():
        path = config.get("local_path", "")
        if path and "<DATA_ROOT>" not in path and Path(path).exists():
            found += 1
        else:
            missing.append(name)

    return {
        "name": "模型路径",
        "status": "PASS" if found > 0 else "INFO",
        "details": {"total": len(models), "found": found, "missing": missing},
        "passed": True
    }


def check_gpu() -> Dict[str, Any]:
    try:
        import subprocess as sp
        result = sp.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                       capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return {
                "name": "GPU",
                "status": "PASS",
                "details": {"available": True, "info": result.stdout.strip()},
                "passed": True
            }
    except Exception:
        pass

    return {
        "name": "GPU",
        "status": "INFO",
        "details": {"available": False, "mode": "CPU"},
        "passed": True
    }


def check_storage(project_root: Path) -> Dict[str, Any]:
    try:
        usage = shutil.disk_usage(str(project_root))
        free_gb = usage.free / (1024**3)
        passed = free_gb >= 10
        return {
            "name": "存储空间",
            "status": "PASS" if passed else "WARN",
            "details": {"free_gb": round(free_gb, 1), "required_gb": 10},
            "passed": passed
        }
    except Exception as e:
        return {"name": "存储空间", "status": "WARN", "details": str(e), "passed": True}


def generate_install_order(checks: List[Dict[str, Any]]) -> List[str]:
    order = []
    for c in checks:
        if c["status"] == "FAIL" or c["status"] == "WARN":
            if c["name"] == "Conda 环境":
                order.append("1. 激活 Conda 环境: conda activate research_agent_v3")
            elif c["name"] == "LLM 配置":
                order.append("2. 设置环境变量: set DEEPSEEK_API_KEY=<your_key>")
            elif c["name"] == "Skill 安装":
                order.append("3. 安装缺失 Skill（运行: python scripts/check_skills.py）")
            elif c["name"] == "MCP 安装":
                order.append("4. 安装缺失 MCP（运行: python scripts/check_mcp.py）")
            elif c["name"] == "Python 环境":
                order.append("1. 安装 Python 3.12 并创建 conda 环境")
    return order


def generate_report(checks: List[Dict[str, Any]], project_root: Path) -> str:
    lines = [
        "# Migration Check Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Project:** {project_root}",
        "",
        "## 检测结果",
        "",
        "| # | 检查项 | 状态 | 详情 |",
        "|---|--------|------|------|",
    ]

    status_emoji = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "INFO": "INFO"}

    for i, c in enumerate(checks, 1):
        details_str = json.dumps(c.get("details", ""), ensure_ascii=False)
        lines.append(f"| {i} | {c['name']} | {status_emoji.get(c['status'], c['status'])} | {details_str} |")

    install_order = generate_install_order(checks)
    if install_order:
        lines.extend(["", "## 建议安装顺序", ""])
        for step in install_order:
            lines.append(step)
        lines.append(f"\n完成后重新运行: python scripts/check_portability.py")
    else:
        lines.extend(["", "## 所有检查通过", "", "系统已就绪，可以启动 Pipeline。"])

    report_path = project_root / "Migration_Check_Report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return str(report_path)


def main() -> int:
    project_root = find_project_root()

    checks = [
        check_python(),
        check_conda(),
        check_skills(project_root),
        check_mcp(project_root),
        check_llm(),
        check_models(project_root),
        check_gpu(),
        check_storage(project_root),
    ]

    print(f"\n{'='*60}")
    print(f"Migration Check Report")
    print(f"{'='*60}")

    all_passed = True
    for c in checks:
        print(f"  {c['name']:20s} {c['status']:6s} {json.dumps(c.get('details',''), ensure_ascii=False)}")
        if not c["passed"]:
            all_passed = False

    report = generate_report(checks, project_root)
    print(f"\nReport: {report}")
    print(f"Overall: {'READY' if all_passed else 'NEEDS ATTENTION'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
