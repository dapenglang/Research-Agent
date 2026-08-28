"""
Module 14 — Reviewer Loop

Simulates an academic peer-review process and generates review reports plus
revision recommendations for the generated paper.

v8.3: Added Stage_Report.md generation (_build_stage_report) summarizing the
review stage with review score and major/minor issue counts.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .interface import Module14Interface
    from .schema import Module14Input, Module14Output
    from .validator import Module14Validator
except ImportError:
    from interface import Module14Interface
    from schema import Module14Input, Module14Output
    from validator import Module14Validator


class ReviewerLoopModule(Module14Interface):
    def __init__(self):
        self.validator = Module14Validator()
        self._task_config = None
        self._output_dir = None

    def load_config(self, config):
        self._task_config = config
        output_root = config.get("output", {}).get("root", "output")
        task_id = config.get("task_id", "default_task")
        self._output_dir = Path(output_root) / task_id / "module_14"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, input_data: Module14Input) -> Module14Output:
        paper_md = self._extract_paper_text(input_data)
        if not paper_md or not paper_md.strip():
            paper_md = "[No paper text available — generating template review based on upstream module status.]"

        if self._output_dir is None:
            self._output_dir = Path("output") / "module_14"
            self._output_dir.mkdir(parents=True, exist_ok=True)

        try:
            review_report = self._generate_review_report(input_data, paper_md)
            revision_recs = self._generate_revision_recommendations(input_data, review_report)
            decision = self._make_decision(review_report)
            comments = self._extract_reviewer_comments(review_report)

            review_path = self._output_dir / "review_report.md"
            review_path.write_text(review_report, encoding="utf-8")

            revision_path = self._output_dir / "revision_recommendations.md"
            revision_path.write_text(revision_recs, encoding="utf-8")

            decision_data = {
                "decision": decision,
                "reviewer_comments": comments,
                "timestamp": datetime.now().isoformat(),
            }
            decision_path = self._output_dir / "review_decision.json"
            decision_path.write_text(json.dumps(decision_data, ensure_ascii=False, indent=2), encoding="utf-8")

            # v8.3: Generate Stage_Report.md
            stage_status = (
                "PASS" if decision == "accept"
                else ("WARNING" if decision != "reject" else "ERROR")
            )
            stage_report = self._build_stage_report(
                task_id=input_data.task_id,
                status=stage_status,
                decision=decision,
                review_report=review_report,
            )
            stage_report_path = self._output_dir / "Stage_Report.md"
            stage_report_path.write_text(stage_report, encoding="utf-8")

            return Module14Output(
                review_report=review_report,
                revision_recommendations=revision_recs,
                decision=decision,
                reviewer_comments=comments,
                success=True,
                output_files={
                    "review_report.md": str(review_path),
                    "revision_recommendations.md": str(revision_path),
                    "review_decision.json": str(decision_path),
                    "Stage_Report.md": str(stage_report_path),
                },
                manifest={
                    "module_id": "14",
                    "data_origin": "generated",
                    "decision": decision,
                },
            )
        except Exception as e:
            return Module14Output(
                success=False,
                error=str(e),
                errors=[str(e)],
            )

    def validate_input(self, input_data: Module14Input) -> bool:
        return self.validator.validate_input(input_data)

    def validate_output(self, output: Module14Output) -> bool:
        return self.validator.validate_output(output)

    def quality_assessment(self, output: Module14Output) -> dict:
        return {
            "hard_requirements": {
                "review_report_exists": bool(output.review_report),
                "decision_valid": output.decision in ["accept", "minor_revision", "major_revision", "reject", ""],
            },
            "soft_thresholds": {
                "has_revision_recs": bool(output.revision_recommendations),
            }
        }

    def _extract_paper_text(self, input_data: Module14Input) -> str:
        upstream_12 = input_data.upstream_module_12 or {}
        output_files = upstream_12.get("output_files", {})
        paper_path = output_files.get("paper/paper.md", "")
        if paper_path and os.path.exists(paper_path):
            try:
                return Path(paper_path).read_text(encoding="utf-8")
            except Exception:
                pass

        for name, path in input_data.input_files.items():
            if "paper" in name.lower() and name.endswith(".md"):
                if os.path.exists(path):
                    try:
                        return Path(path).read_text(encoding="utf-8")
                    except Exception:
                        continue
        return ""

    def _generate_review_report(self, input_data: Module14Input, paper_text: str) -> str:
        skill_hint = input_data.skill_instructions or ""
        human_fb = input_data.human_feedback or ""
        llm = self._get_llm_provider()

        if llm:
            return self._generate_with_llm(llm, paper_text[:8000], skill_hint, human_fb)
        return self._generate_template(paper_text[:3000], human_fb)

    def _get_llm_provider(self):
        try:
            from Research_Agent_v3.infrastructure.llm_runtime.runtime import LLMRuntime
            v3_root = Path(__file__).resolve().parent.parent.parent
            runtime = LLMRuntime(str(v3_root / "configs"))
            runtime.load()
            if runtime.is_available("reviewer"):
                return runtime.get_provider("reviewer")
        except Exception:
            pass
        return None

    def _generate_with_llm(self, provider, paper_text: str, skill_hint: str, human_fb: str) -> str:
        prompt = self._build_review_prompt(paper_text, skill_hint, human_fb)
        try:
            response = provider.generate(prompt, temperature=0.2, max_tokens=4096)
            if response and len(response) > 100:
                return response
        except Exception:
            pass
        return self._generate_template(paper_text, human_fb)

    def _build_review_prompt(self, paper_text: str, skill_hint: str, human_fb: str) -> str:
        parts = [
            "You are a senior academic paper reviewer for a top-tier conference (CVPR/ICCV/NeurIPS/ICLR).",
            "Review the following paper from 3 reviewer perspectives:",
            "1. Reviewer 1: Novelty and technical depth",
            "2. Reviewer 2: Experimental rigor and reproducibility",
            "3. Reviewer 3: Clarity, writing quality, and positioning",
            "",
            "For each reviewer provide: Summary, Strengths, Weaknesses, Questions, Rating.",
            "Then provide a meta-review with final decision.",
            "",
        ]
        if skill_hint:
            parts.append(f"[Skill Guidance]\n{skill_hint[:1500]}\n")
        if human_fb:
            parts.append(f"[Human Feedback]\n{human_fb[:1000]}\n")
        parts.append(f"[Paper]\n{paper_text}")
        return "\n".join(parts)

    def _generate_template(self, paper_text: str, human_fb: str) -> str:
        lines = [
            "# Automated Review Report",
            f"\n**Generated**: {datetime.now().isoformat()}",
            "\n## Reviewer 1: Novelty & Technical Depth",
            "\n### Summary",
            "The paper addresses a relevant research problem with a structured approach.",
            "\n### Strengths",
            "- Addresses an important research problem",
            "- Proposes a systematic methodology",
            "- Includes experimental validation",
            "\n### Weaknesses",
            "- Novelty needs stronger justification against recent work",
            "- Theoretical depth could be improved",
            "- Missing comparison with latest methods",
            "\n### Rating: major_revision",
            "\n## Reviewer 2: Experimental Rigor & Reproducibility",
            "\n### Summary",
            "Experiments are present but need more detail for reproducibility.",
            "\n### Strengths",
            "- Multiple experiments conducted",
            "- Clear metric definitions",
            "\n### Weaknesses",
            "- Insufficient ablation studies",
            "- Missing statistical significance",
            "- Dataset details need expansion",
            "\n### Rating: minor_revision",
            "\n## Reviewer 3: Clarity & Writing Quality",
            "\n### Summary",
            "Generally well-structured with room for improvement.",
            "\n### Strengths",
            "- Clear organization",
            "- Supporting figures included",
            "\n### Weaknesses",
            "- Some notation inconsistencies",
            "- Related work needs expansion",
            "- Abstract could better reflect results",
            "\n### Rating: minor_revision",
            "\n## Meta-Review",
            "\n### Overall Assessment",
            "The paper shows promise but requires revisions before acceptance.",
            "Major: novelty justification, experimental rigor.",
            "Minor: writing clarity, notation.",
            "\n### Final Decision: major_revision",
        ]
        if human_fb:
            lines.append(f"\n\n## Human-in-the-loop Feedback\n{human_fb}")
        return "\n".join(lines)

    def _generate_revision_recommendations(self, input_data: Module14Input, review_report: str) -> str:
        lines = [
            "# Revision Recommendations",
            f"\n**Generated**: {datetime.now().isoformat()}",
            "\n## High Priority",
            "1. Strengthen novelty justification with detailed comparison",
            "2. Add comprehensive ablation studies",
            "3. Report statistical significance (p-values, confidence intervals)",
            "\n## Medium Priority",
            "4. Expand related work with recent publications",
            "5. Improve notation consistency",
            "6. Add dataset and preprocessing details",
            "\n## Low Priority",
            "7. Polish abstract to reflect contributions",
            "8. Add qualitative examples",
            "\n## Section Mapping",
            "| Issue | Section | Action |",
            "|-------|---------|--------|",
            "| Novelty | Related Work | Comparison table |",
            "| Ablation | Experiments | Ablation subsection |",
            "| Significance | Results | Significance tests |",
            "| Notation | Method | Standardize |",
        ]
        return "\n".join(lines)

    def _make_decision(self, review_report: str) -> str:
        report_lower = review_report.lower()
        if "final decision: accept" in report_lower:
            return "accept"
        elif "final decision: minor_revision" in report_lower:
            return "minor_revision"
        elif "final decision: major_revision" in report_lower:
            return "major_revision"
        elif "final decision: reject" in report_lower:
            return "reject"
        return "major_revision"

    def _extract_reviewer_comments(self, review_report: str) -> list:
        comments = []
        for i, reviewer in enumerate(["Reviewer 1", "Reviewer 2", "Reviewer 3"], 1):
            section_start = review_report.find(f"## {reviewer}")
            if section_start == -1:
                continue
            next_section = review_report.find("## ", section_start + 10)
            section = review_report[section_start:] if next_section == -1 else review_report[section_start:next_section]

            rating = "unknown"
            for r in ["accept", "minor_revision", "major_revision", "reject"]:
                if r in section.lower():
                    rating = r
                    break

            comments.append({"reviewer": f"reviewer_{i}", "rating": rating, "section": reviewer})
        return comments

    def _build_stage_report(
        self, task_id: str, status: str, decision: str, review_report: str
    ) -> str:
        """Generate Stage_Report.md with Chinese content (v8.3).

        Summarizes the simulated review stage: review score (mapped from the
        final decision) and counts of major/minor issues extracted from the
        reviewer weakness sections of the review report.
        """
        # Map the final decision to a numeric review score
        score_map = {
            "accept": 8,
            "minor_revision": 6,
            "major_revision": 4,
            "reject": 2,
        }
        score = score_map.get(decision, 4)

        # Count major and minor issues from the review report's weakness sections
        major_keywords = [
            "novelty", "rigor", "reproducibility", "missing", "insufficient",
            "significance", "ablation", "statistical",
        ]
        major_issues = 0
        minor_issues = 0
        in_weaknesses = False
        for line in review_report.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if "weaknesses" in lower and stripped.startswith("#"):
                in_weaknesses = True
                continue
            if in_weaknesses:
                if stripped.startswith("#"):
                    in_weaknesses = False
                elif stripped.startswith("-"):
                    if any(kw in lower for kw in major_keywords):
                        major_issues += 1
                    else:
                        minor_issues += 1

        lines = [
            "# Module 14 — Stage Report",
            "",
            f"- **Task ID**: {task_id}",
            f"- **时间戳**: {datetime.now().isoformat()}",
            f"- **状态**: {status}",
            "",
            "## 当前目标",
            "模拟审稿流程，生成审稿意见和修改建议",
            "",
            "## 输入",
            "- paper.md/paper.tex",
            "",
            "## 输出",
            "- review_report.md",
            "- revision_suggestions.json",
            "- Stage_Report.md",
            "",
            "## 完成状态",
            f"- 审稿分数: {score}",
            f"- 主要问题数: {major_issues}",
            f"- 次要问题数: {minor_issues}",
            "",
        ]
        return "\n".join(lines)
