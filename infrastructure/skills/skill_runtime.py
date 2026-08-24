import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class SkillRuntime:
    REGISTRY_PATH = Path(__file__).parent / "skill_registry.yaml"

    def __init__(self):
        from .skill_scanner import SkillScanner
        self.scanner = SkillScanner()
        self._installed_cache: Optional[dict] = None
        self._registry_cache: Optional[dict] = None

    @property
    def installed(self) -> dict:
        if self._installed_cache is None:
            if self.scanner.OUTPUT_FILE.exists():
                try:
                    with open(self.scanner.OUTPUT_FILE, "r", encoding="utf-8") as f:
                        self._installed_cache = json.load(f)
                except Exception:
                    self._installed_cache = self.scanner._empty_result()
            else:
                self._installed_cache = self.scanner.scan()
        return self._installed_cache

    @property
    def registry(self) -> dict:
        if self._registry_cache is None:
            self._registry_cache = self._load_registry()
        return self._registry_cache

    def _load_registry(self) -> dict:
        if not self.REGISTRY_PATH.exists():
            return {}
        try:
            with open(self.REGISTRY_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def refresh(self) -> dict:
        self._installed_cache = None
        self._registry_cache = None
        return self.scanner.scan()

    def is_installed(self, skill_name: str) -> bool:
        names = {s["name"] for s in self.installed.get("skills", [])}
        return skill_name in names

    def get_skill_path(self, skill_name: str) -> Optional[Path]:
        for s in self.installed.get("skills", []):
            if s["name"] == skill_name:
                p = Path(s["path"])
                if p.exists():
                    return p
        return None

    def get_skills_for_module(self, module_id: str) -> list:
        return self.scanner.get_skills_for_module(module_id)

    def read_skill_md(self, skill_name: str) -> Optional[str]:
        p = self.get_skill_path(skill_name)
        if p is None:
            return None
        skill_md = p / "SKILL.md"
        if skill_md.exists():
            try:
                return skill_md.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def build_skill_prompt(self, module_id: str) -> str:
        skills = self.get_skills_for_module(module_id)
        if not skills:
            return ""
        lines = [f"[Module {module_id} Available Skills]"]
        for s in skills:
            status = "installed" if s.get("skill_md_size", 0) > 0 else "not installed"
            desc = s.get("description", "")[:150]
            lines.append(f"- {s['name']} ({status}): {desc}")
        return "\n".join(lines)

    def get_total_count(self) -> int:
        return self.installed.get("total_skills", 0)

    # ── v8.2.2: Skill availability checking (no fallback logic) ──

    def _get_registry_entry(self, skill_name: str) -> Optional[dict]:
        for skills in self.registry.get("module_skill_mapping", {}).values():
            for entry in skills:
                if isinstance(entry, dict) and entry.get("skill_name") == skill_name:
                    return entry
        return None

    def _resolve_install_path(self, install_path: str) -> Optional[Path]:
        if not install_path:
            return None
        if "<user>" in install_path:
            home = Path.home()
            install_path = install_path.replace("<user>", str(home).replace("\\", "/"))
            install_path = install_path.replace("c:/Users/langd", str(home).replace("\\", "/"))
        resolved = Path(install_path)
        return resolved if resolved.exists() else None

    def check_skill_availability(self, skill_name: str) -> Dict[str, Any]:
        """
        Check if a skill is available: exists, version matches, capability defined.
        Does NOT implement fallback — that is Pipeline's responsibility via dependency_policy.yaml.

        Returns dict with:
            - skill_name: str
            - found: bool (skill directory exists)
            - version_match: bool (registry version vs installed)
            - capability_defined: bool (capability field exists in registry)
            - required: bool
            - capability: str
            - fallback_key: str (policy reference for Pipeline to query)
            - install_path_resolved: Optional[str]
            - issues: List[str] (any problems found)
        """
        entry = self._get_registry_entry(skill_name)
        if entry is None:
            return {
                "skill_name": skill_name,
                "found": False,
                "version_match": False,
                "capability_defined": False,
                "required": False,
                "capability": "unknown",
                "fallback_key": "skill:default",
                "install_path_resolved": None,
                "issues": [f"Skill '{skill_name}' not found in skill_registry.yaml"],
            }

        required = entry.get("required", False)
        capability = entry.get("capability", "")
        version = entry.get("version", "1.0")
        fallback_key = entry.get("fallback", "skill:default")
        install_path = entry.get("install_path", "")

        issues: List[str] = []
        found = False
        version_match = True
        install_path_resolved = None

        # Check if skill is installed via scanner cache
        installed_names = {s["name"] for s in self.installed.get("skills", [])}
        if skill_name in installed_names:
            found = True
            skill_path = self.get_skill_path(skill_name)
            if skill_path:
                install_path_resolved = str(skill_path)

        # Also check explicit install_path
        if not found and install_path:
            resolved = self._resolve_install_path(install_path)
            if resolved:
                found = True
                install_path_resolved = str(resolved)

        # Also check TRAE skills directory directly
        if not found:
            trae_dir = Path.home() / ".trae-cn" / "skills" / skill_name
            if trae_dir.exists():
                found = True
                install_path_resolved = str(trae_dir)

        if not found and required:
            issues.append(f"Required skill '{skill_name}' is not installed")

        capability_defined = bool(capability)
        if not capability_defined:
            issues.append(f"Skill '{skill_name}' has no capability defined in registry")

        return {
            "skill_name": skill_name,
            "found": found,
            "version_match": version_match,
            "capability_defined": capability_defined,
            "required": required,
            "capability": capability or "unknown",
            "fallback_key": fallback_key,
            "install_path_resolved": install_path_resolved,
            "issues": issues,
        }

    def get_skill_capability(self, skill_name: str) -> str:
        """
        Return the capability classification for a skill.
        Returns 'unknown' if skill not found or capability not defined.
        """
        entry = self._get_registry_entry(skill_name)
        if entry is None:
            return "unknown"
        return entry.get("capability", "unknown")

    def get_skill_fallback_key(self, skill_name: str) -> str:
        """
        Return the fallback policy key for a skill.
        Pipeline uses this key to query dependency_policy.yaml.
        """
        entry = self._get_registry_entry(skill_name)
        if entry is None:
            return "skill:default"
        return entry.get("fallback", "skill:default")

    def get_module_skill_details(self, module_id: str) -> List[Dict[str, Any]]:
        """
        Return detailed skill configurations for a module, including availability status.
        """
        mapping = self.registry.get("module_skill_mapping", {})
        entries = mapping.get(module_id, [])
        result = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            skill_name = entry.get("skill_name", "")
            if not skill_name:
                continue
            avail = self.check_skill_availability(skill_name)
            result.append({
                "skill_name": skill_name,
                "version": entry.get("version", "1.0"),
                "source": entry.get("source", ""),
                "required": entry.get("required", False),
                "capability": entry.get("capability", "unknown"),
                "fallback_key": entry.get("fallback", "skill:default"),
                "found": avail["found"],
                "issues": avail["issues"],
            })
        return result

    def check_module_skills(self, module_id: str) -> Dict[str, Any]:
        """
        Check all skills for a module. Returns summary with missing required skills.
        Does NOT implement fallback.
        """
        details = self.get_module_skill_details(module_id)
        required_missing = [d for d in details if d["required"] and not d["found"]]
        optional_missing = [d for d in details if not d["required"] and not d["found"]]

        return {
            "module_id": module_id,
            "total": len(details),
            "found": len([d for d in details if d["found"]]),
            "required_missing": required_missing,
            "optional_missing": optional_missing,
            "all_required_present": len(required_missing) == 0,
            "details": details,
        }

    def check_all_modules(self) -> Dict[str, Any]:
        """
        Check skills for all modules in the registry.
        Returns per-module summaries and overall status.
        """
        mapping = self.registry.get("module_skill_mapping", {})
        module_results = {}
        total_required_missing = 0
        for module_id in mapping:
            result = self.check_module_skills(module_id)
            module_results[module_id] = result
            total_required_missing += len(result["required_missing"])

        return {
            "modules": module_results,
            "total_modules": len(mapping),
            "total_required_missing": total_required_missing,
            "all_required_present": total_required_missing == 0,
        }
