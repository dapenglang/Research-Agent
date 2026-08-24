import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


class SkillScanner:
    TRAE_SKILLS_DIR = Path("c:/Users/langd/.trae-cn/skills")
    OUTPUT_FILE = Path(__file__).parent / "installed_skills.json"

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or self.TRAE_SKILLS_DIR

    def scan(self) -> dict:
        if not self.skills_dir.exists():
            return self._empty_result()

        skills = []
        for item in sorted(self.skills_dir.iterdir()):
            if not item.is_dir():
                continue
            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue
            info = self._parse_skill_md(skill_md, item.name)
            if info:
                skills.append(info)

        result = {
            "scan_time": datetime.now().isoformat(),
            "skills_dir": str(self.skills_dir),
            "total_skills": len(skills),
            "skills": skills,
        }
        self.OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result

    def _parse_skill_md(self, skill_md: Path, dir_name: str) -> Optional[dict]:
        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception:
            return None

        name = dir_name
        description = ""

        lines = text.splitlines()
        in_frontmatter = False
        fm_lines = []
        body_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                fm_lines.append(line)
            else:
                body_lines.append(line)

        for line in fm_lines:
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"').strip("'")

        if not description and body_lines:
            for line in body_lines[:20]:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith(">"):
                    description = stripped[:300]
                    break

        return {
            "name": name,
            "directory": dir_name,
            "path": str(skill_md.parent),
            "description": description[:500],
            "skill_md_size": skill_md.stat().st_size,
        }

    def _empty_result(self) -> dict:
        return {
            "scan_time": datetime.now().isoformat(),
            "skills_dir": str(self.skills_dir),
            "total_skills": 0,
            "skills": [],
        }

    def get_skills_for_module(self, module_id: str) -> list:
        registry_path = Path(__file__).parent / "skill_registry.yaml"
        if not registry_path.exists():
            return []
        try:
            import yaml
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = yaml.safe_load(f)
        except Exception:
            return []

        mappings = registry.get("module_skill_mapping", {})
        skill_entries = mappings.get(module_id, [])
        installed = self.load_installed()
        installed_map = {s["name"]: s for s in installed}
        result = []
        for entry in skill_entries:
            if isinstance(entry, dict):
                sn = entry.get("skill_name", "")
            else:
                sn = entry
            if not sn:
                continue
            if sn in installed_map:
                result.append(installed_map[sn])
            else:
                result.append({"name": sn, "directory": sn, "path": "", "description": "not installed", "skill_md_size": 0})
        return result

    def load_installed(self) -> list:
        if self.OUTPUT_FILE.exists():
            try:
                with open(self.OUTPUT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("skills", [])
            except Exception:
                pass
        return []
