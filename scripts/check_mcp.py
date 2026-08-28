#!/usr/bin/env python
"""
MCP Availability Check — v8.2.2

Checks installed/configured/tested status for each MCP server.
Updates mcp_registry.yaml status fields.
Outputs MCP_Install_Request.md when MCPs are missing.

Usage:
    python scripts/check_mcp.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


def find_project_root() -> Path:
    current = Path(__file__).resolve().parent.parent
    if (current / "configs").exists():
        return current
    return Path.cwd()


def load_mcp_registry(project_root: Path) -> Dict[str, Any]:
    registry_path = project_root / "infrastructure" / "mcp" / "mcp_registry.yaml"
    if not registry_path.exists():
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_command_available(command: str) -> bool:
    return shutil.which(command) is not None


def check_mcp_installed(server_config: Dict[str, Any]) -> bool:
    command = server_config.get("command", "")
    if not command:
        return False
    return check_command_available(command)


def check_mcp_configured(server_config: Dict[str, Any]) -> bool:
    env = server_config.get("env", {})
    if not env:
        return True
    for key, val in env.items():
        if not val and not os.environ.get(key, ""):
            return False
    return True


def check_mcp_tested(server_name: str, server_config: Dict[str, Any]) -> bool:
    command = server_config.get("command", "")
    args = server_config.get("args", [])
    if not check_command_available(command):
        return False
    try:
        proc = subprocess.run(
            [command, "--help"] + args[:1],
            capture_output=True,
            timeout=5,
            text=True
        )
        return proc.returncode == 0 or proc.returncode == 2
    except Exception:
        return False


def check_mcp(project_root: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "MCP 检测",
        "passed": True,
        "total": 0,
        "installed_count": 0,
        "configured_count": 0,
        "tested_count": 0,
        "missing": [],
        "details": []
    }

    registry = load_mcp_registry(project_root)
    servers = registry.get("mcp_servers", {})
    if not servers:
        result["passed"] = False
        result["error"] = "mcp_registry.yaml not found or empty"
        return result

    updated = False
    for name, config in servers.items():
        if not config.get("enabled", False):
            continue

        result["total"] += 1

        installed = check_mcp_installed(config)
        configured = check_mcp_configured(config)

        old_installed = config.get("installed", False)
        old_configured = config.get("configured", False)

        if installed != old_installed:
            config["installed"] = installed
            updated = True
        else:
            config["installed"] = installed

        if configured != old_configured:
            config["configured"] = configured
            updated = True
        else:
            config["configured"] = configured

        tested = check_mcp_tested(name, config)
        config["tested"] = tested
        updated = True

        if installed:
            result["installed_count"] += 1
        if configured:
            result["configured_count"] += 1
        if tested:
            result["tested_count"] += 1

        detail = {
            "name": name,
            "installed": installed,
            "configured": configured,
            "tested": tested,
            "enabled": config.get("enabled", False),
            "fallback": config.get("fallback", "mcp:default"),
            "command": config.get("command", ""),
            "install_method": config.get("install_method", "")
        }
        result["details"].append(detail)

        if not installed:
            result["missing"].append(detail)

    if updated:
        registry_path = project_root / "infrastructure" / "mcp" / "mcp_registry.yaml"
        with open(registry_path, "w", encoding="utf-8") as f:
            yaml.dump(registry, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    if result["missing"]:
        result["passed"] = False

    return result


def generate_install_request(result: Dict[str, Any], project_root: Path) -> str:
    lines = [
        "# MCP Install Request",
        "",
        f"**Generated:** {__import__('datetime').datetime.now().isoformat()}",
        "",
        "## Missing MCP Servers",
        "",
    ]

    for m in result["missing"]:
        lines.extend([
            f"### {m['name']}",
            f"- Command: {m['command']}",
            f"- Install method: {m['install_method']}",
            f"- Fallback: {m['fallback']}",
            f"- Install command: {m['command']} {' '.join(['install'] if m['command'] == 'uvx' else [])}",
            "",
        ])

    lines.extend([
        "## Installation Steps",
        "",
        "1. Install the MCP server using the command above",
        "2. Configure any required environment variables",
        "3. Test: python scripts/check_mcp.py",
        "",
    ])

    report_path = project_root / "MCP_Install_Request.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return str(report_path)


def main() -> int:
    project_root = find_project_root()
    result = check_mcp(project_root)

    print(f"\n{'='*60}")
    print(f"MCP Check Report")
    print(f"{'='*60}")
    print(f"Total enabled MCPs: {result['total']}")
    print(f"Installed: {result['installed_count']}")
    print(f"Configured: {result['configured_count']}")
    print(f"Tested: {result['tested_count']}")
    print(f"Status: {'PASS' if result['passed'] else 'FAIL'}")

    if result["details"]:
        print("\nDetails:")
        for d in result["details"]:
            inst = "Y" if d["installed"] else "N"
            conf = "Y" if d["configured"] else "N"
            test = "Y" if d["tested"] else "N"
            print(f"  {d['name']:20s} installed={inst} configured={conf} tested={test}")

    if result["missing"]:
        report = generate_install_request(result, project_root)
        print(f"\nInstall request generated: {report}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
