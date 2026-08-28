"""
Module 15 — Research Memory

Collects and synthesizes stage reports, decision logs, and lessons learned
from all upstream modules into a persistent research memory document for
cross-session continuity.

v8.3 additions:
  - Stage_Report.md generation
  - Decision log tracing from upstream module outputs
  - Lessons learned extraction from pipeline warnings/errors
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .interface import Module15Interface
    from .schema import Module15Input, Module15Output
    from .validator import Module15Validator
except ImportError:
    from interface import Module15Interface
    from schema import Module15Input, Module15Output
    from validator import Module15Validator


class ResearchMemoryModule(Module15Interface):
    MODULE_ID = "15"
    MODULE_NAME = "Research Memory"

    def __init__(self):
        self.validator = Module15Validator()
        self._config: Dict[str, Any] = {}
        self._output_dir: Optional[Path] = None

    def load_config(self, config: Dict[str, Any]) -> None:
        self._config = config
        output_root = config.get("output", {}).get("root", "output")
        task_id = config.get("task_id", "default_task")
        self._output_dir = Path(output_root) / task_id / "module_15"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, input_data: Module15Input) -> Module15Output:
        if self._output_dir is None:
            self._output_dir = Path("output") / "module_15"
            self._output_dir.mkdir(parents=True, exist_ok=True)

        warnings: List[str] = []
        errors: List[str] = []

        stage_reports = self._collect_stage_reports(input_data)
        decisions = self._collect_decisions(input_data)
        lessons = self._extract_lessons(stage_reports, input_data)
        pipeline_summary = self._build_pipeline_summary(stage_reports, decisions)

        memory_md = self._build_research_memory(
            input_data.task_id, stage_reports, decisions, lessons, pipeline_summary
        )
        decision_md = self._build_decision_log(decisions)
        lessons_md = self._build_lessons_learned(lessons)
        stage_md = self._build_stage_report(
            input_data.task_id, stage_reports, decisions, lessons
        )

        memory_path = self._output_dir / "research_memory.md"
        memory_path.write_text(memory_md, encoding="utf-8")

        decision_path = self._output_dir / "decision_log.md"
        decision_path.write_text(decision_md, encoding="utf-8")

        lessons_path = self._output_dir / "lessons_learned.md"
        lessons_path.write_text(lessons_md, encoding="utf-8")

        stage_path = self._output_dir / "Stage_Report.md"
        stage_path.write_text(stage_md, encoding="utf-8")

        return Module15Output(
            research_memory=memory_md,
            decision_log=decision_md,
            lessons_learned=lessons_md,
            success=True,
            output_files={
                "research_memory.md": str(memory_path),
                "decision_log.md": str(decision_path),
                "lessons_learned.md": str(lessons_path),
                "Stage_Report.md": str(stage_path),
            },
            manifest={
                "module_id": "15",
                "stage_reports_collected": len(stage_reports),
                "decisions_traced": len(decisions),
                "lessons_extracted": len(lessons),
            },
            warnings=warnings,
            errors=errors,
        )

    def validate_input(self, input_data: Module15Input) -> bool:
        return self.validator.validate_input(input_data)

    def validate_output(self, output: Module15Output) -> bool:
        return self.validator.validate_output(output)

    def quality_assessment(self, output: Module15Output) -> dict:
        return {
            "hard_requirements": {
                "research_memory_exists": bool(output.research_memory),
                "decision_log_exists": bool(output.decision_log),
            },
            "soft_thresholds": {
                "has_lessons": bool(output.lessons_learned),
                "output_file_count": len(output.output_files),
            },
        }

    def _collect_stage_reports(self, input_data: Module15Input) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []

        for name, path in input_data.input_files.items():
            if "Stage_Report" not in name and "stage_report" not in name:
                continue
            try:
                content = Path(path).read_text(encoding="utf-8")
                module_id = self._extract_module_id(name, content)
                reports.append({
                    "module_id": module_id,
                    "file_name": name,
                    "content": content,
                    "path": path,
                })
            except Exception:
                pass

        upstream = input_data.upstream_modules or {}
        for mod_id, mod_data in upstream.items():
            if isinstance(mod_data, dict):
                output_files = mod_data.get("output_files", {})
                for fname, fpath in output_files.items():
                    if "Stage_Report" in fname and os.path.exists(fpath):
                        try:
                            content = Path(fpath).read_text(encoding="utf-8")
                            reports.append({
                                "module_id": mod_id,
                                "file_name": fname,
                                "content": content,
                                "path": fpath,
                            })
                        except Exception:
                            pass

        reports.sort(key=lambda r: r["module_id"])
        return reports

    def _extract_module_id(self, file_name: str, content: str) -> str:
        for line in content.splitlines()[:5]:
            if "Module" in line:
                for token in line.split():
                    if token.isdigit():
                        return token.zfill(2)
        parts = file_name.replace("\\", "/").split("/")
        for part in parts:
            if part.startswith("module_"):
                return part.replace("module_", "")
        return "??"

    def _collect_decisions(self, input_data: Module15Input) -> List[Dict[str, Any]]:
        decisions: List[Dict[str, Any]] = []

        for name, path in input_data.input_files.items():
            if not name.endswith(".json"):
                continue
            key_words = ["decision", "review_decision", "analysis_report"]
            if not any(kw in name for kw in key_words):
                continue
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                decisions.append({
                    "file": name,
                    "path": path,
                    "data": data,
                })
            except Exception:
                pass

        upstream = input_data.upstream_modules or {}
        for mod_id, mod_data in upstream.items():
            if isinstance(mod_data, dict):
                manifest = mod_data.get("manifest", {})
                if manifest:
                    decisions.append({
                        "module_id": mod_id,
                        "manifest": manifest,
                    })

        return decisions

    def _extract_lessons(
        self, stage_reports: List[Dict], input_data: Module15Input
    ) -> List[str]:
        lessons: List[str] = []

        for report in stage_reports:
            content = report.get("content", "")
            in_section = False
            for line in content.splitlines():
                stripped = line.strip()
                lower = stripped.lower()
                if "警告" in stripped or "错误" in stripped or "warning" in lower:
                    if stripped.startswith("-"):
                        lessons.append(f"[Module {report['module_id']}] {stripped[1:].strip()}")
                if "教训" in lower or "lesson" in lower:
                    in_section = True
                    continue
                if in_section and stripped.startswith("-"):
                    lessons.append(f"[Module {report['module_id']}] {stripped[1:].strip()}")
                elif in_section and stripped.startswith("#"):
                    in_section = False

        upstream = input_data.upstream_modules or {}
        for mod_id, mod_data in upstream.items():
            if isinstance(mod_data, dict):
                for w in mod_data.get("warnings", []):
                    lessons.append(f"[Module {mod_id}] Warning: {w}")
                for e in mod_data.get("errors", []):
                    lessons.append(f"[Module {mod_id}] Error: {e}")

        if not lessons:
            lessons.append("[Pipeline] No critical warnings or errors detected across modules.")

        return lessons

    def _build_pipeline_summary(
        self, stage_reports: List[Dict], decisions: List[Dict]
    ) -> Dict[str, Any]:
        module_ids = [r["module_id"] for r in stage_reports]
        return {
            "total_stage_reports": len(stage_reports),
            "modules_covered": module_ids,
            "total_decisions": len(decisions),
            "pipeline_complete": len(stage_reports) >= 10,
        }

    def _build_research_memory(
        self,
        task_id: str,
        stage_reports: List[Dict],
        decisions: List[Dict],
        lessons: List[str],
        summary: Dict[str, Any],
    ) -> str:
        lines = [
            "# Research Memory",
            "",
            f"**Task ID:** {task_id}",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Pipeline Status:** {'Complete' if summary['pipeline_complete'] else 'Partial'}",
            "",
            "---",
            "",
            "## 1. Pipeline Overview",
            "",
            f"- Stage Reports Collected: {summary['total_stage_reports']}",
            f"- Modules Covered: {', '.join(summary['modules_covered'])}",
            f"- Decision Points: {summary['total_decisions']}",
            "",
            "## 2. Module Summaries",
            "",
        ]

        for report in stage_reports:
            mod_id = report["module_id"]
            content = report["content"]
            first_lines = content.splitlines()[:10]
            status = "unknown"
            for line in first_lines:
                if "状态" in line or "Status" in line:
                    status = line.split(":", 1)[-1].strip() if ":" in line else line
                    break

            lines.append(f"### Module {mod_id}")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Source:** {report['file_name']}")
            lines.append("")
            summary_lines = [l for l in first_lines if l.strip() and not l.startswith("#")][:3]
            for sl in summary_lines:
                lines.append(f"> {sl}")
            lines.append("")

        lines.extend([
            "## 3. Decision Chain",
            "",
        ])

        for d in decisions:
            if "module_id" in d:
                lines.append(f"- **Module {d['module_id']}**: manifest recorded")
            elif "data" in d:
                data = d["data"]
                decision_val = data.get("decision", data.get("decision", ""))
                lines.append(f"- **{d['file']}**: {decision_val or 'recorded'}")

        lines.extend([
            "",
            "## 4. Lessons Learned",
            "",
        ])

        for lesson in lessons:
            lines.append(f"- {lesson}")

        lines.extend([
            "",
            "## 5. Research Artifacts Index",
            "",
            "### Papers & Literature",
            "- Literature Database: data/literature/literature_database.json",
            "- Paper Assets: data/literature/pdf/, data/literature/latex/",
            "",
            "### Innovation & Method",
            "- Innovation Candidates: output/{task_id}/module_05/innovation_candidates.json",
            "- Method Specification: output/{task_id}/module_06/method_spec.json",
            "- Theory Analysis: output/{task_id}/module_06/theory_analysis.md",
            "",
            "### Experiments",
            "- Experiment Plan: output/{task_id}/module_07/experiment_plan.yaml",
            "- Synthetic Results: output/{task_id}/module_08/synthetic_results.json",
            "- Real Results: output/{task_id}/module_09/",
            "- Analysis: output/{task_id}/module_10/analysis_report.json",
            "",
            "### Paper",
            "- Paper Markdown: output/{task_id}/module_12/paper/paper.md",
            "- Paper LaTeX: output/{task_id}/module_12/paper/paper.tex",
            "- Paper DOCX: output/{task_id}/module_12/paper/paper.docx",
            "- References: output/{task_id}/module_13/references.bib",
            "- Review: output/{task_id}/module_14/review_report.md",
            "",
            "---",
            f"*Generated by Research Agent v8.3 Module 15 at {datetime.now().isoformat()}*",
        ])

        return "\n".join(lines)

    def _build_decision_log(self, decisions: List[Dict]) -> str:
        lines = [
            "# Decision Log",
            "",
            f"**Generated:** {datetime.now().isoformat()}",
            "",
            "| # | Source | Decision | Details |",
            "|---|--------|----------|---------|",
        ]

        for i, d in enumerate(decisions, 1):
            if "data" in d:
                data = d["data"]
                decision_val = data.get("decision", "")
                details = str(data.get("reasoning", data.get("reason", "")))[:80]
                lines.append(f"| {i} | {d['file']} | {decision_val} | {details} |")
            elif "module_id" in d:
                manifest = d.get("manifest", {})
                lines.append(f"| {i} | Module {d['module_id']} | {manifest.get('decision', 'N/A')} | manifest |")

        if len(lines) == 4:
            lines.append("| - | (no decisions recorded) | - | - |")

        return "\n".join(lines)

    def _build_lessons_learned(self, lessons: List[str]) -> str:
        lines = [
            "# Lessons Learned",
            "",
            f"**Generated:** {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
            f"Total lessons extracted: {len(lessons)}",
            "",
            "## Details",
            "",
        ]

        for lesson in lessons:
            lines.append(f"- {lesson}")

        lines.extend([
            "",
            "## Recommendations for Future Runs",
            "",
            "1. Ensure all modules generate Stage_Report.md for complete traceability",
            "2. Review warnings and errors before proceeding to downstream modules",
            "3. Verify LLM availability before starting the pipeline",
            "4. Check literature database completeness (>= 50 papers)",
            "5. Validate experiment backend registration before Module 08",
            "",
            "---",
            f"*Generated by Research Agent v8.3 Module 15*",
        ])

        return "\n".join(lines)

    def _build_stage_report(
        self,
        task_id: str,
        stage_reports: List[Dict],
        decisions: List[Dict],
        lessons: List[str],
    ) -> str:
        lines = [
            "# Module 15 — Research Memory Stage Report",
            "",
            f"- **Task ID**: {task_id}",
            f"- **时间戳**: {datetime.now().isoformat()}",
            f"- **状态**: 完成",
            "",
            "## 当前目标",
            "收集所有模块的阶段报告，生成科研记忆文档，支持跨会话连续性",
            "",
            "## 输入",
            "- 各模块 Stage_Report.md",
            "- review_decision.json",
            "- analysis_report.json",
            "- upstream_modules context",
            "",
            "## 输出",
            "- research_memory.md",
            "- decision_log.md",
            "- lessons_learned.md",
            "- Stage_Report.md",
            "",
            "## 完成状态",
            f"- 收集阶段报告数: {len(stage_reports)}",
            f"- 决策记录数: {len(decisions)}",
            f"- 提取教训数: {len(lessons)}",
            f"- 覆盖模块: {', '.join(r['module_id'] for r in stage_reports) or '(无)'}",
            "",
        ]

        return "\n".join(lines)
