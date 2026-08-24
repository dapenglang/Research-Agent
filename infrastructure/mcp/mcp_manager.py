import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class MCPManager:
    REGISTRY_PATH = Path(__file__).parent / "mcp_registry.yaml"

    def __init__(self):
        self._servers = None

    @property
    def servers(self) -> dict:
        if self._servers is None:
            self._servers = self._load_registry()
        return self._servers

    def _load_registry(self) -> dict:
        if not self.REGISTRY_PATH.exists():
            return {}
        try:
            with open(self.REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("mcp_servers", {})
        except Exception:
            return {}

    def get_server(self, name: str) -> Optional[dict]:
        return self.servers.get(name)

    def list_enabled(self) -> dict:
        return {k: v for k, v in self.servers.items() if v.get("enabled", False)}

    def list_by_category(self, category: str) -> dict:
        return {
            k: v for k, v in self.servers.items()
            if v.get("category") == category and v.get("enabled", False)
        }

    def get_config_json(self) -> dict:
        result = {}
        for name, cfg in self.list_enabled().items():
            entry = {
                "command": cfg.get("command", ""),
                "args": cfg.get("args", []),
            }
            env = cfg.get("env", {})
            resolved_env = {}
            for k, v in env.items():
                if isinstance(v, str) and v.startswith("$"):
                    resolved_env[k] = os.environ.get(v[1:], "")
                elif v:
                    resolved_env[k] = v
            if resolved_env:
                entry["env"] = resolved_env
            result[name] = entry
        return {"mcpServers": result}

    def is_available(self, name: str) -> bool:
        server = self.get_server(name)
        if not server or not server.get("enabled"):
            return False
        env = server.get("env", {})
        for k, v in env.items():
            if isinstance(v, str) and v.startswith("$"):
                if not os.environ.get(v[1:]):
                    return False
            elif v == "" and k.endswith("KEY"):
                return False
        return True

    def summary(self) -> str:
        lines = ["[MCP Server Registry Summary]"]
        enabled = self.list_enabled()
        lines.append(f"Enabled servers: {len(enabled)}")
        for name, cfg in enabled.items():
            avail = self.is_available(name)
            status = "READY" if avail else "CONFIGURED (missing env)"
            lines.append(f"  - {name} [{cfg.get('category', '?')}]: {status}")
        disabled = {k: v for k, v in self.servers.items() if not v.get("enabled")}
        if disabled:
            lines.append(f"Disabled servers: {len(disabled)}")
            for name in disabled:
                lines.append(f"  - {name}")
        return "\n".join(lines)

    # ── v8.2.2: MCP availability checking (no fallback logic) ──

    def _check_installed(self, server_config: dict) -> bool:
        """Check if the MCP command is installed on the system."""
        command = server_config.get("command", "")
        if not command:
            return False
        return shutil.which(command) is not None

    def _check_configured(self, server_config: dict) -> bool:
        """Check if all required environment variables are set."""
        env = server_config.get("env", {})
        if not env:
            return True
        for key, val in env.items():
            if not val and not os.environ.get(key, ""):
                return False
        return True

    def _check_tested(self, server_config: dict) -> bool:
        """Attempt a quick connection test to the MCP server."""
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        if not self._check_installed(server_config):
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

    def check_availability(self, name: str) -> Dict[str, Any]:
        """
        Check MCP service availability: installed, configured, tested.
        Updates the registry YAML with current status.
        Does NOT implement fallback — that is Pipeline's responsibility via dependency_policy.yaml.

        Returns dict with:
            - name: str
            - enabled: bool
            - installed: bool
            - configured: bool
            - tested: bool
            - fallback_key: str (policy reference for Pipeline to query)
            - issues: List[str]
        """
        server = self.get_server(name)
        if server is None:
            return {
                "name": name,
                "enabled": False,
                "installed": False,
                "configured": False,
                "tested": False,
                "fallback_key": "mcp:default",
                "issues": [f"MCP '{name}' not found in registry"],
            }

        enabled = server.get("enabled", False)
        if not enabled:
            return {
                "name": name,
                "enabled": False,
                "installed": False,
                "configured": False,
                "tested": False,
                "fallback_key": server.get("fallback", "mcp:default"),
                "issues": [f"MCP '{name}' is disabled"],
            }

        installed = self._check_installed(server)
        configured = self._check_configured(server)
        tested = self._check_tested(server) if installed else False

        # Update registry with current status
        server["installed"] = installed
        server["configured"] = configured
        server["tested"] = tested

        issues: List[str] = []
        if not installed:
            command = server.get("command", "")
            issues.append(f"Command '{command}' not found — install via {server.get('install_method', 'unknown')}")
        if not configured:
            issues.append(f"Environment variables not configured for '{name}'")
        if installed and configured and not tested:
            issues.append(f"MCP '{name}' installed and configured but connection test failed")

        return {
            "name": name,
            "enabled": True,
            "installed": installed,
            "configured": configured,
            "tested": tested,
            "fallback_key": server.get("fallback", "mcp:default"),
            "issues": issues,
        }

    def check_all_availability(self) -> Dict[str, Any]:
        """
        Check all enabled MCP servers. Updates registry YAML with current status.
        Returns per-server results and overall summary.
        """
        results = {}
        installed_count = 0
        configured_count = 0
        tested_count = 0
        missing: List[dict] = []

        for name in self.list_enabled():
            result = self.check_availability(name)
            results[name] = result
            if result["installed"]:
                installed_count += 1
            if result["configured"]:
                configured_count += 1
            if result["tested"]:
                tested_count += 1
            if not result["installed"]:
                missing.append(result)

        # Persist updated status to registry YAML
        self._save_registry()

        return {
            "servers": results,
            "total_enabled": len(results),
            "installed_count": installed_count,
            "configured_count": configured_count,
            "tested_count": tested_count,
            "missing": missing,
            "all_installed": len(missing) == 0,
        }

    def get_mcp_fallback_key(self, name: str) -> str:
        """
        Return the fallback policy key for an MCP server.
        Pipeline uses this key to query dependency_policy.yaml.
        """
        server = self.get_server(name)
        if server is None:
            return "mcp:default"
        return server.get("fallback", "mcp:default")

    def get_mcp_category(self, name: str) -> str:
        """Return the category for an MCP server."""
        server = self.get_server(name)
        if server is None:
            return "unknown"
        return server.get("category", "unknown")

    def _save_registry(self) -> None:
        """Save updated server status back to registry YAML."""
        if not self.REGISTRY_PATH.exists():
            return
        try:
            with open(self.REGISTRY_PATH, "r", encoding="utf-8") as f:
                full_registry = yaml.safe_load(f) or {}
            full_registry["mcp_servers"] = self.servers
            with open(self.REGISTRY_PATH, "w", encoding="utf-8") as f:
                yaml.dump(full_registry, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        except Exception:
            pass
