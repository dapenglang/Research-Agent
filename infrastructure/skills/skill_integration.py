import re
from pathlib import Path
from typing import Optional


class SkillIntegration:
    def __init__(self):
        from .skill_runtime import SkillRuntime
        self.runtime = SkillRuntime()

    def enhance_context(self, module_id: str, context: dict) -> dict:
        skills = self.runtime.get_skills_for_module(module_id)
        if not skills:
            return context

        skill_contexts = []
        for skill in skills:
            if skill.get("skill_md_size", 0) > 0:
                content = self.runtime.read_skill_md(skill["name"])
                if content:
                    extracted = self._extract_key_instructions(content, skill["name"])
                    if extracted:
                        skill_contexts.append(extracted)

        if skill_contexts:
            context["skill_instructions"] = "\n\n---\n\n".join(skill_contexts)
            context["available_skills"] = [s["name"] for s in skills if s.get("skill_md_size", 0) > 0]
        else:
            context["skill_instructions"] = ""
            context["available_skills"] = []

        return context

    def _extract_key_instructions(self, skill_md: str, skill_name: str, max_chars: int = 2000) -> str:
        lines = skill_md.splitlines()
        key_lines = [f"## Skill: {skill_name}"]
        in_description = False
        in_instructions = False
        char_count = 0

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("---"):
                continue

            if stripped.startswith("#"):
                header = stripped.lower()
                if any(kw in header for kw in ["description", "when to use", "usage", "instructions", "workflow", "how to"]):
                    in_instructions = True
                    key_lines.append(f"\n{stripped}")
                    char_count += len(stripped) + 1
                elif any(kw in header for kw in ["example", "reference", "see also", "deprecated"]):
                    in_instructions = False
                else:
                    if in_instructions and char_count < max_chars:
                        key_lines.append(f"\n{stripped}")
                        char_count += len(stripped) + 1
            elif in_instructions and char_count < max_chars:
                if stripped:
                    key_lines.append(line)
                    char_count += len(line) + 1

        result = "\n".join(key_lines[:100])
        if len(result) > max_chars:
            result = result[:max_chars] + "..."
        return result

    def get_skill_summary(self, module_id: str) -> str:
        skills = self.runtime.get_skills_for_module(module_id)
        if not skills:
            return ""
        lines = [f"[Module {module_id} Skill Integration]"]
        for s in skills:
            status = "OK" if s.get("skill_md_size", 0) > 0 else "NOT INSTALLED"
            lines.append(f"  - {s['name']}: {status}")
        return "\n".join(lines)

    def read_human_feedback(self, feedback_dir: Path, feedback_type: str) -> str:
        feedback_map = {
            "innovation": "innovation_feedback.md",
            "method": "method_feedback.md",
            "review": "review_response.md",
        }
        filename = feedback_map.get(feedback_type, f"{feedback_type}_feedback.md")
        feedback_path = feedback_dir / filename
        if feedback_path.exists():
            try:
                content = feedback_path.read_text(encoding="utf-8").strip()
                if content and not content.startswith("# Innovation Feedback"):
                    return content
                real_lines = []
                for line in content.splitlines():
                    if line.strip().startswith("<!--") or line.strip().startswith("-->"):
                        continue
                    if line.strip().startswith(">"):
                        continue
                    if line.strip().startswith("#"):
                        continue
                    real_lines.append(line)
                real_content = "\n".join(real_lines).strip()
                if real_content:
                    return real_content
            except Exception:
                pass
        return ""
