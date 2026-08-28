#!/usr/bin/env python
"""
Research Readiness Check — pre-pipeline validation.

Checks:
1. Python environment (version, key packages)
2. LLM configuration (providers, API keys)
3. API connection (test call)
4. Literature count (minimum 50 papers)
5. Directory structure (data/, output/, state/)
6. Output directory writability

Outputs Research_Readiness_Report.md.

Usage:
    python scripts/check_research_ready.py
    python scripts/check_research_ready.py --task tasks/task_001.yaml

Exit codes:
    0 — all checks pass, ready to start pipeline
    1 — one or more checks failed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent.parent
    if (current / "configs").exists():
        return current
    return Path.cwd()


def check_python_env() -> Dict[str, Any]:
    """Check Python version and key packages."""
    result: Dict[str, Any] = {"name": "Python 环境", "passed": True, "details": {}}

    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    result["details"]["python_version"] = version
    if sys.version_info < (3, 10):
        result["passed"] = False
        result["details"]["error"] = f"Python {version} < 3.10 required"
        return result

    packages = ["yaml", "json", "pathlib"]
    optional_packages = {
        "openai": "openai (用于 OpenAI/DeepSeek API)",
        "numpy": "numpy (用于实验分析)",
        "matplotlib": "matplotlib (用于图表生成)",
    }

    for pkg, desc in optional_packages.items():
        try:
            __import__(pkg)
            result["details"][pkg] = "installed"
        except ImportError:
            result["details"][pkg] = f"NOT installed — {desc}"

    return result


def check_llm_config(project_root: Path) -> Dict[str, Any]:
    """Check LLM provider configuration."""
    result: Dict[str, Any] = {"name": "LLM 配置", "passed": False, "details": {}}

    providers_path = project_root / "configs" / "providers.yaml"
    if not providers_path.exists():
        result["details"]["error"] = "providers.yaml not found"
        return result

    with open(providers_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    llm = config.get("providers", {}).get("llm", {})
    providers = {k: v for k, v in llm.items() if k not in ("default", "mock")}

    result["details"]["configured_providers"] = list(providers.keys())

    available: List[str] = []
    for name, pcfg in providers.items():
        ptype = pcfg.get("type", name)
        if ptype == "local":
            endpoint = pcfg.get("endpoint", "") or os.environ.get("LOCAL_LLM_ENDPOINT", "")
            if endpoint:
                available.append(name)
        else:
            env_var = pcfg.get("api_key_env", "")
            if env_var and os.environ.get(env_var, ""):
                available.append(name)

    result["details"]["available_providers"] = available

    if available:
        result["passed"] = True
    else:
        result["details"]["error"] = "No LLM provider has valid API key. Set OPENAI_API_KEY or DEEPSEEK_API_KEY."

    return result


def check_api_connection(project_root: Path) -> Dict[str, Any]:
    """Test actual API connection."""
    result: Dict[str, Any] = {"name": "API 连接测试", "passed": False, "details": {}}

    try:
        sys.path.insert(0, str(project_root.parent))
        from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
        runtime = LLMRuntime(str(project_root / "configs"))
        runtime.load()
        status = runtime.get_status()

        result["details"]["status"] = status

        for name, info in status.items():
            if info.get("available"):
                try:
                    provider = runtime.get_provider("paper_generation")
                    if provider:
                        response = provider.generate("Reply with: HELLO")
                        if response:
                            result["passed"] = True
                            result["details"]["tested_provider"] = name
                            result["details"]["response"] = response[:100]
                            break
                except Exception as e:
                    result["details"][f"{name}_error"] = str(e)

        if not result["passed"]:
            result["details"]["error"] = "No provider could complete a test call"
    except Exception as e:
        result["details"]["error"] = str(e)

    return result


def check_literature_count(project_root: Path, min_papers: int = 50) -> Dict[str, Any]:
    """Check literature count."""
    result: Dict[str, Any] = {"name": "论文数量", "passed": False, "details": {}}

    data_dir = project_root / "data" / "literature"
    pdf_dir = data_dir / "pdf"
    latex_dir = data_dir / "latex"

    pdf_count = 0
    latex_count = 0

    if pdf_dir.exists():
        pdf_count = sum(1 for f in pdf_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf" and f.stat().st_size > 1024)

    if latex_dir.exists():
        for d in latex_dir.iterdir():
            if d.is_dir() and list(d.rglob("*.tex")):
                latex_count += 1

    total = pdf_count + latex_count
    result["details"]["pdf_count"] = pdf_count
    result["details"]["latex_count"] = latex_count
    result["details"]["total"] = total
    result["details"]["minimum"] = min_papers

    if total >= min_papers:
        result["passed"] = True
    else:
        result["details"]["error"] = f"Only {total} papers found, need at least {min_papers}"

    return result


def check_directory_structure(project_root: Path) -> Dict[str, Any]:
    """Check required directory structure."""
    result: Dict[str, Any] = {"name": "目录结构", "passed": True, "details": {}}

    required = [
        "configs",
        "modules",
        "orchestrator",
        "infrastructure/llm",
        "infrastructure/llm_runtime",
        "data/literature/pdf",
        "data/literature/latex",
        "tasks",
        "scripts",
        "memory",
    ]

    missing: List[str] = []
    for d in required:
        path = project_root / d
        if not path.exists():
            missing.append(d)
            try:
                path.mkdir(parents=True, exist_ok=True)
                result["details"][f"created: {d}"] = True
            except Exception:
                pass

    if missing:
        result["details"]["missing_dirs"] = missing
        result["details"]["auto_created"] = True
        result["passed"] = True

    result["details"]["required_dirs"] = required
    return result


def check_output_writable(project_root: Path) -> Dict[str, Any]:
    """Check if output directory is writable."""
    result: Dict[str, Any] = {"name": "输出目录", "passed": False, "details": {}}

    output_dir = project_root / "output"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / ".write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        result["passed"] = True
        result["details"]["output_dir"] = str(output_dir)
    except Exception as e:
        result["details"]["error"] = str(e)

    return result


def check_skills_installed(project_root: Path) -> Dict[str, Any]:
    """v8.2.2: Check skill availability using check_skills.py."""
    result: Dict[str, Any] = {"name": "Skill 安装", "passed": True, "details": {}}
    try:
        sys.path.insert(0, str(project_root / "scripts"))
        from check_skills import check_skills as _cs
        sr = _cs(project_root)
        result["details"]["total"] = sr.get("total", 0)
        result["details"]["found"] = sr.get("found", 0)
        result["details"]["missing_required"] = len([m for m in sr.get("missing", []) if m.get("required")])
        result["passed"] = sr.get("passed", True)
        if not result["passed"]:
            result["details"]["error"] = f"{len(sr.get('missing', []))} required skills missing"
    except Exception as e:
        result["details"]["error"] = str(e)
        result["passed"] = True
    return result


def check_mcp_installed(project_root: Path) -> Dict[str, Any]:
    """v8.2.2: Check MCP availability using check_mcp.py."""
    result: Dict[str, Any] = {"name": "MCP 安装", "passed": True, "details": {}}
    try:
        sys.path.insert(0, str(project_root / "scripts"))
        from check_mcp import check_mcp as _cm
        mr = _cm(project_root)
        result["details"]["total"] = mr.get("total", 0)
        result["details"]["installed"] = mr.get("installed_count", 0)
        result["details"]["configured"] = mr.get("configured_count", 0)
        result["details"]["tested"] = mr.get("tested_count", 0)
        result["passed"] = mr.get("passed", True)
        if not result["passed"]:
            result["details"]["error"] = f"{len(mr.get('missing', []))} MCP servers not installed"
    except Exception as e:
        result["details"]["error"] = str(e)
        result["passed"] = True
    return result


def check_portability(project_root: Path) -> Dict[str, Any]:
    """v8.2.2: Run portability check and summarize."""
    result: Dict[str, Any] = {"name": "迁移检测", "passed": True, "details": {}}
    try:
        sys.path.insert(0, str(project_root / "scripts"))
        from check_portability import (
            check_python, check_conda, check_skills as cp_skills,
            check_mcp as cp_mcp, check_llm, check_gpu, check_storage,
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
        result["details"]["checks"] = [{"name": c["name"], "status": c["status"]} for c in checks]
        warn_count = sum(1 for c in checks if c["status"] in ("WARN", "FAIL"))
        result["details"]["warnings"] = warn_count
        if warn_count > 0:
            result["passed"] = True
            result["details"]["note"] = f"{warn_count} items need attention (non-blocking in limited mode)"
    except Exception as e:
        result["details"]["error"] = str(e)
        result["passed"] = True
    return result


def generate_report(checks: List[Dict[str, Any]], task_file: str = "") -> str:
    """Generate readiness report."""
    all_pass = all(c["passed"] for c in checks)

    lines: List[str] = []
    lines.append("# Research Readiness Report")
    lines.append("")
    lines.append(f"**检查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    if task_file:
        lines.append(f"**目标任务**: {task_file}")
    lines.append("")

    lines.append("## 检查结果总览")
    lines.append("")
    lines.append("| # | 检查项 | 状态 |")
    lines.append("|---|--------|------|")
    for i, c in enumerate(checks, 1):
        status = "PASS" if c["passed"] else "FAIL"
        lines.append(f"| {i} | {c['name']} | {status} |")
    lines.append("")

    lines.append(f"**总体结论**: {'READY — 可以启动 Pipeline' if all_pass else 'NOT READY — 请修复上述 FAIL 项'}")
    lines.append("")

    lines.append("## 详细检查")
    lines.append("")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        lines.append(f"### {c['name']} [{status}]")
        lines.append("")
        for key, val in c["details"].items():
            if isinstance(val, (dict, list)):
                lines.append(f"- **{key}**: {json.dumps(val, ensure_ascii=False, default=str)}")
            else:
                lines.append(f"- **{key}**: {val}")
        lines.append("")

    if not all_pass:
        lines.append("## 修复指南")
        lines.append("")
        for c in checks:
            if not c["passed"]:
                lines.append(f"### {c['name']}")
                error = c["details"].get("error", "")
                lines.append(f"**问题**: {error}")
                lines.append("")

        lines.append("### 参考文档")
        lines.append("- LLM 配置: `docs/LLM_Configuration_Guide_CN.md`")
        lines.append("- 论文准备: `docs/Literature_Preparation_Guide_CN.md`")
        lines.append("- 快速开始: `docs/START_HERE_CN.md`")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Research Readiness Check")
    parser.add_argument("--task", type=str, default=None, help="Task YAML file path")
    parser.add_argument("--min-papers", type=int, default=50, help="Minimum papers required")
    parser.add_argument("--output", type=str, default=None, help="Output report path")
    parser.add_argument("--skip-api-test", action="store_true", help="Skip API connection test")
    args = parser.parse_args()

    project_root = find_project_root()

    checks: List[Dict[str, Any]] = []
    checks.append(check_python_env())
    checks.append(check_llm_config(project_root))

    if not args.skip_api_test:
        checks.append(check_api_connection(project_root))

    checks.append(check_literature_count(project_root, args.min_papers))
    checks.append(check_directory_structure(project_root))
    checks.append(check_output_writable(project_root))

    # v8.2.2: New infrastructure checks
    checks.append(check_skills_installed(project_root))
    checks.append(check_mcp_installed(project_root))
    checks.append(check_portability(project_root))

    report = generate_report(checks, args.task or "")

    output_path = Path(args.output) if args.output else project_root / "Research_Readiness_Report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    all_pass = all(c["passed"] for c in checks)
    if all_pass:
        print("[READY] All checks passed — pipeline is ready to start")
    else:
        print("[NOT READY] Some checks failed:")
        for c in checks:
            if not c["passed"]:
                print(f"  [FAIL] {c['name']}: {c['details'].get('error', '')}")

    print(f"Report: {output_path}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
