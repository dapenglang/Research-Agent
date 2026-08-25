"""
Module 05 -- Innovation & Novelty Reasoning
Implementation (facade/adapter pattern).

Wraps the existing reasoning components:
  - reasoning.scientific_reasoner.innovation_generator.InnovationGenerator
  - reasoning.scientific_reasoner.novelty_checker.NoveltyChecker
  - reasoning.scientific_reasoner.causal_analyzer.CausalAnalyzer
  - reasoning.hypothesis_generator.hypothesis_generator.HypothesisGenerator

Produces:
  - innovation_candidates.json
  - novelty_analysis.md
  - final_research_direction.md
  - Stage_Report.md (v8.3)

v8.3 upgrades:
  - Collision detection: check if innovation is too similar to existing papers
  - Stage_Report.md for pipeline tracking
  - Enhanced innovation candidates with collision check results
  - Real literature-driven innovation grounded in paper analysis
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Project-root bootstrap.
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from reasoning.scientific_reasoner.innovation_generator import InnovationGenerator
from reasoning.scientific_reasoner.novelty_checker import NoveltyChecker
from reasoning.scientific_reasoner.causal_analyzer import CausalAnalyzer
from reasoning.hypothesis_generator.hypothesis_generator import HypothesisGenerator

from .interface import (
    Module05Interface,
    InnovationReasoningInput,
    InnovationReasoningOutput,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM provider adapter (shared logic, duplicated per-module for autonomy).
# ---------------------------------------------------------------------------

class LLMProviderAdapter:
    """Thin adapter bridging v3 LLM providers to existing reasoning code."""

    def __init__(self, v3_provider: Any) -> None:
        self._provider = v3_provider

    def generate(self, prompt: str, context: str = "") -> str:
        try:
            return self._provider.generate(prompt, context=context)
        except TypeError:
            return self._provider.generate(prompt)

    def is_available(self) -> bool:
        if hasattr(self._provider, "is_available"):
            return self._provider.is_available()
        return True

    def get_info(self) -> Dict[str, Any]:
        if hasattr(self._provider, "get_info"):
            return self._provider.get_info()
        return {"provider_type": type(self._provider).__name__}


# ---------------------------------------------------------------------------
# Module 05 implementation
# ---------------------------------------------------------------------------

class InnovationReasoningModule(Module05Interface):
    """Facade that wraps InnovationGenerator, NoveltyChecker,
    CausalAnalyzer, and HypothesisGenerator."""

    MODULE_ID = "05"
    MODULE_NAME = "Innovation & Novelty Reasoning"
    VERSION = "1.0.0"

    def __init__(self, llm_provider: Any = None) -> None:
        self._raw_provider = llm_provider
        self._llm_provider: Optional[LLMProviderAdapter] = None
        if llm_provider is not None:
            self._llm_provider = LLMProviderAdapter(llm_provider)

        self._config: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Interface implementation
    # ------------------------------------------------------------------

    def load_config(self, config: Dict[str, Any]) -> None:
        self._config = config or {}
        logger.info("Module 05 config loaded: %s", list(self._config.keys()))

    def validate_input(self, input_data: InnovationReasoningInput) -> bool:
        """Validate that all required inputs are present."""
        if not input_data.input_files.get("gap_candidates.json"):
            logger.error("Missing required input file: gap_candidates.json")
            return False
        return True

    def execute(
        self, input_data: InnovationReasoningInput
    ) -> InnovationReasoningOutput:
        """Run the innovation-reasoning pipeline."""
        warnings: List[str] = []
        errors: List[str] = []
        output_files: Dict[str, str] = {}

        output_dir = self._config.get(
            "output_dir",
            os.path.join(tempfile.gettempdir(), f"module05_{input_data.task_id}"),
        )
        os.makedirs(output_dir, exist_ok=True)

        # ----------------------------------------------------------
        # 1. Load inputs.
        # ----------------------------------------------------------
        gap_candidates = self._load_json(
            input_data.input_files.get("gap_candidates.json")
        )
        paper_analyses = self._load_json(
            input_data.input_files.get("paper_analysis.json")
        )
        contradiction_map = self._load_json(
            input_data.input_files.get("contradiction_map.json")
        )

        # Build research context.
        research_context = self._build_research_context(
            gap_candidates, paper_analyses, contradiction_map
        )

        # ----------------------------------------------------------
        # 2. Causal analysis.
        # ----------------------------------------------------------
        causal_analyzer = CausalAnalyzer(
            llm_provider=self._llm_provider,
            llm_enabled=self._llm_provider is not None,
        )
        causal_result: Dict[str, Any] = {}
        try:
            observation = research_context.get("problem", "Research landscape analysis")
            causal_result = causal_analyzer.analyze_causal_chain(observation)
        except Exception as exc:
            logger.warning("CausalAnalyzer failed: %s", exc)
            warnings.append(f"Causal analysis error: {exc}")

        # ----------------------------------------------------------
        # 3. Innovation generation.
        # ----------------------------------------------------------
        innovation_generator = InnovationGenerator(
            llm_provider=self._llm_provider,
            llm_enabled=self._llm_provider is not None,
        )
        innovations: List[Dict[str, Any]] = []
        try:
            num_innovations = self._config.get("num_innovations", 3)
            innovations = innovation_generator.generate_innovations(
                research_context, num_innovations=num_innovations
            )
        except Exception as exc:
            logger.warning("InnovationGenerator failed: %s", exc)
            warnings.append(f"Innovation generation error: {exc}")

        # ----------------------------------------------------------
        # 4. Novelty checking.
        # ----------------------------------------------------------
        novelty_db = self._build_novelty_database(paper_analyses)
        novelty_checker = NoveltyChecker(
            llm_provider=self._llm_provider,
            llm_enabled=self._llm_provider is not None,
            database=novelty_db,
        )
        novelty_reports: List[Dict[str, Any]] = []
        for inn in innovations:
            try:
                report = novelty_checker.check_against_database(inn)
                novelty_reports.append(report)
            except Exception as exc:
                logger.warning("NoveltyChecker failed for innovation: %s", exc)
                novelty_reports.append({
                    "novelty_score": 0.0,
                    "novelty_level": "unknown",
                    "similar_works": [],
                    "check_summary": f"Check failed: {exc}",
                    "database_size": len(novelty_db),
                })

        # ----------------------------------------------------------
        # 5. Hypothesis generation (for final research direction).
        # ----------------------------------------------------------
        gap_analysis_path = input_data.input_files.get("gap_candidates.json", "")
        hypothesis_path = os.path.join(output_dir, "_hypotheses.md")
        hypothesis_generator = HypothesisGenerator(
            llm_provider=self._llm_provider,
        )
        try:
            # If we have a gap analysis file, use it; otherwise write
            # a minimal one.
            if not gap_analysis_path or not os.path.exists(gap_analysis_path):
                gap_analysis_path = os.path.join(output_dir, "_gap_analysis.md")
                self._write_minimal_gap_analysis(
                    gap_analysis_path, gap_candidates, research_context
                )
            hypothesis_generator.generate(
                gap_analysis_path=gap_analysis_path,
                output_path=hypothesis_path,
            )
        except Exception as exc:
            logger.warning("HypothesisGenerator failed: %s", exc)
            warnings.append(f"Hypothesis generation error: {exc}")

        # ----------------------------------------------------------
        # 6. Produce output files.
        # ----------------------------------------------------------
        # innovation_candidates.json
        candidates = self._build_innovation_candidates(
            innovations, novelty_reports, gap_candidates
        )

        # v8.3: Collision detection — check if innovation is too similar to existing papers
        collision_results = self._check_collisions(candidates, paper_analyses)
        for i, candidate in enumerate(candidates.get("candidates", [])):
            if i < len(collision_results):
                candidate["collision_check"] = collision_results[i]

        candidates_path = os.path.join(output_dir, "innovation_candidates.json")
        with open(candidates_path, "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)
        output_files["innovation_candidates.json"] = candidates_path

        # novelty_analysis.md
        novelty_md = self._build_novelty_analysis_md(
            innovations, novelty_reports, causal_result
        )
        novelty_path = os.path.join(output_dir, "novelty_analysis.md")
        with open(novelty_path, "w", encoding="utf-8") as f:
            f.write(novelty_md)
        output_files["novelty_analysis.md"] = novelty_path

        # final_research_direction.md
        direction_md = self._build_final_direction_md(
            innovations, novelty_reports, causal_result, hypothesis_path
        )
        direction_path = os.path.join(output_dir, "final_research_direction.md")
        with open(direction_path, "w", encoding="utf-8") as f:
            f.write(direction_md)
        output_files["final_research_direction.md"] = direction_path

        # v8.3: Stage_Report.md
        stage_report = self._build_stage_report(
            input_data.task_id, candidates, collision_results, warnings, errors
        )
        stage_path = os.path.join(output_dir, "Stage_Report.md")
        with open(stage_path, "w", encoding="utf-8") as f:
            f.write(stage_report)
        output_files["Stage_Report.md"] = stage_path

        output = InnovationReasoningOutput(
            task_id=input_data.task_id,
            output_files=output_files,
            manifest={},
            warnings=warnings,
            errors=errors,
        )

        if not self.validate_output(output):
            warnings.append("Output validation reported issues")

        output.manifest = self.write_manifest(output)
        return output

    def validate_output(self, output: InnovationReasoningOutput) -> bool:
        """Validate that all required outputs are present."""
        required = ["innovation_candidates.json", "novelty_analysis.md",
                     "final_research_direction.md"]
        for name in required:
            if name not in output.output_files:
                logger.error("Missing required output file: %s", name)
                return False
            path = output.output_files[name]
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                logger.error("Output file empty or missing: %s", name)
                return False
        return True

    def quality_assessment(
        self, output: InnovationReasoningOutput
    ) -> Dict[str, Any]:
        details: Dict[str, Any] = {}

        candidates_path = output.output_files.get("innovation_candidates.json", "")
        candidates = self._safe_load_json(candidates_path)
        cand_count = len(candidates.get("candidates", [])) if candidates else 0
        details["innovation_candidates_count"] = cand_count
        details["candidates_hard_pass"] = cand_count >= 1

        direction_path = output.output_files.get("final_research_direction.md", "")
        direction_nonempty = (
            os.path.exists(direction_path)
            and os.path.getsize(direction_path) > 0
        )
        details["direction_nonempty"] = direction_nonempty
        details["direction_hard_pass"] = direction_nonempty

        novelty_path = output.output_files.get("novelty_analysis.md", "")
        novelty_nonempty = (
            os.path.exists(novelty_path) and os.path.getsize(novelty_path) > 0
        )
        details["novelty_nonempty"] = novelty_nonempty

        passed = details["candidates_hard_pass"] and details["direction_hard_pass"]

        return {
            "passed": passed,
            "details": details,
            "assessed_at": datetime.now().isoformat(),
        }

    def write_manifest(
        self, output: InnovationReasoningOutput
    ) -> Dict[str, Any]:
        return {
            "module_id": self.MODULE_ID,
            "module_name": self.MODULE_NAME,
            "version": self.VERSION,
            "task_id": output.task_id,
            "outputs": list(output.output_files.keys()),
            "output_paths": output.output_files,
            "warnings": output.warnings,
            "errors": output.errors,
            "created_at": datetime.now().isoformat(),
        }

    def write_report(self, output: InnovationReasoningOutput) -> str:
        qa = self.quality_assessment(output)
        lines = [
            f"# Module {self.MODULE_ID} -- {self.MODULE_NAME}",
            "",
            f"**Task ID:** {output.task_id}",
            f"**Generated:** {datetime.now().isoformat()}",
            "",
            "## Output Files",
            "",
        ]
        for name, path in output.output_files.items():
            lines.append(f"- `{name}`: `{path}`")
        lines.extend([
            "",
            "## Quality Assessment",
            "",
            f"- **Overall passed:** {qa['passed']}",
        ])
        for k, v in qa.get("details", {}).items():
            lines.append(f"- {k}: {v}")
        if output.warnings:
            lines.extend(["", "## Warnings", ""])
            for w in output.warnings:
                lines.append(f"- {w}")
        if output.errors:
            lines.extend(["", "## Errors", ""])
            for e in output.errors:
                lines.append(f"- {e}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # v8.3: Collision Detection & Stage Report
    # ------------------------------------------------------------------

    def _check_collisions(
        self,
        candidates: Dict[str, Any],
        paper_analyses: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """v8.3: Check if innovation candidates collide with existing papers.

        For each candidate, compare its title/description against all papers
        in the analysis database. If similarity is too high, flag as collision.
        """
        papers = []
        if isinstance(paper_analyses, list):
            papers = paper_analyses
        elif isinstance(paper_analyses, dict):
            papers = paper_analyses.get("papers", paper_analyses.get("analyses", []))

        results: List[Dict[str, Any]] = []
        candidates_list = candidates.get("candidates", [])

        for candidate in candidates_list:
            cand_title = candidate.get("title", "").lower()
            cand_desc = candidate.get("description", "").lower()
            cand_text = f"{cand_title} {cand_desc}"

            collisions: List[Dict[str, Any]] = []
            max_similarity = 0.0

            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                paper_title = paper.get("title", paper.get("paper_id", "")).lower()
                paper_method = paper.get("methodology", paper.get("method", "")).lower()
                paper_text = f"{paper_title} {paper_method}"

                similarity = self._compute_text_similarity(cand_text, paper_text)
                if similarity > 0.3:
                    collisions.append({
                        "paper_id": paper.get("paper_id", paper.get("title", "")),
                        "title": paper.get("title", ""),
                        "similarity": round(similarity, 3),
                    })
                    if similarity > max_similarity:
                        max_similarity = similarity

            is_collision = max_similarity > 0.5
            results.append({
                "has_collision": is_collision,
                "max_similarity": round(max_similarity, 3),
                "collision_risk": "high" if max_similarity > 0.6 else ("medium" if max_similarity > 0.4 else "low"),
                "similar_papers": collisions[:5],
                "total_similar": len(collisions),
            })

        return results

    @staticmethod
    def _compute_text_similarity(text1: str, text2: str) -> float:
        """Compute simple text similarity based on word overlap."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    def _build_stage_report(
        self,
        task_id: str,
        candidates: Dict[str, Any],
        collision_results: List[Dict[str, Any]],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        """v8.3: Build Stage_Report.md for Module 05."""
        candidates_list = candidates.get("candidates", [])
        collision_count = sum(1 for c in collision_results if c.get("has_collision", False))
        high_risk = sum(1 for c in collision_results if c.get("collision_risk") == "high")
        medium_risk = sum(1 for c in collision_results if c.get("collision_risk") == "medium")

        lines = [
            "# Module 05 — Innovation & Novelty Reasoning Stage Report",
            "",
            f"**Task ID:** {task_id}",
            f"**Timestamp:** {datetime.now().isoformat()}",
            f"**Status:** {'COMPLETED' if not errors else 'FAILED'}",
            "",
            "## 当前目标",
            "",
            "基于文献空白和矛盾点，生成创新候选并通过撞车检测验证新颖性。",
            "",
            "## 输入",
            "",
            "- gap_candidates.json (研究空白)",
            "- paper_analysis.json (论文分析)",
            "- contradiction_map.json (矛盾图)",
            "",
            "## 输出",
            "",
            f"- innovation_candidates.json ({len(candidates_list)} 个候选)",
            f"- novelty_analysis.md (新颖性分析)",
            f"- final_research_direction.md (最终方向)",
            f"- Stage_Report.md (阶段报告)",
            "",
            "## 创新候选概览",
            "",
        ]

        for i, cand in enumerate(candidates_list):
            title = cand.get("title", f"Candidate {i+1}")
            novelty = cand.get("novelty_score", 0)
            feasibility = cand.get("feasibility_score", 0)
            collision = cand.get("collision_check", {})
            risk = collision.get("collision_risk", "N/A") if collision else "N/A"
            lines.append(f"### 候选 {i+1}: {title[:80]}")
            lines.append(f"- 新颖性: {novelty:.2f}")
            lines.append(f"- 可行性: {feasibility:.2f}")
            lines.append(f"- 撞车风险: {risk}")
            lines.append("")

        lines.extend([
            "## 撞车检测统计",
            "",
            f"- 总候选数: {len(candidates_list)}",
            f"- 撞车数: {collision_count}",
            f"- 高风险: {high_risk}",
            f"- 中风险: {medium_risk}",
            "",
        ])

        if warnings:
            lines.extend(["## 警告", ""])
            for w in warnings:
                lines.append(f"- {w}")
        if errors:
            lines.extend(["## 错误", ""])
            for e in errors:
                lines.append(f"- {e}")

        return "\n".join(lines)

    @staticmethod
    def _load_json(path: Optional[str]) -> Dict[str, Any]:
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def _safe_load_json(path: str) -> Optional[Dict[str, Any]]:
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _build_research_context(
        self,
        gap_candidates: Dict[str, Any],
        paper_analyses: Dict[str, Any],
        contradiction_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the research context dict for InnovationGenerator."""
        gaps = gap_candidates.get("gaps", [])
        gap_descriptions = [g.get("description", "") for g in gaps if g.get("description")]

        # Extract existing methods from paper analyses.
        papers = []
        if isinstance(paper_analyses, list):
            papers = paper_analyses
        elif isinstance(paper_analyses, dict):
            papers = paper_analyses.get("papers", paper_analyses.get("analyses", []))

        existing_methods = [
            p.get("methodology", p.get("method", ""))
            for p in papers
            if isinstance(p, dict) and (p.get("methodology") or p.get("method"))
        ]
        limitations = [
            p.get("limitations", "")
            for p in papers
            if isinstance(p, dict) and p.get("limitations")
        ]
        # Normalise list limitations.
        normalised_lims: List[str] = []
        for lim in limitations:
            if isinstance(lim, list):
                normalised_lims.extend(str(x) for x in lim)
            elif isinstance(lim, str) and lim:
                normalised_lims.append(lim)

        problem = gap_descriptions[0] if gap_descriptions else "Research gap analysis"
        domain = "general"
        # Try to infer domain from paper methods.
        methods_text = " ".join(existing_methods).lower()
        if any(kw in methods_text for kw in ["vision", "image", "visual", "vlm"]):
            domain = "computer_vision"
        elif any(kw in methods_text for kw in ["nlp", "language", "text", "llm"]):
            domain = "natural_language_processing"
        elif any(kw in methods_text for kw in ["graph", "gnn"]):
            domain = "graph_learning"

        return {
            "problem": problem,
            "domain": domain,
            "existing_methods": existing_methods if existing_methods else ["unknown"],
            "limitations": normalised_lims if normalised_lims else ["unspecified"],
            "gap_analysis": "\n".join(gap_descriptions),
        }

    def _build_novelty_database(
        self, paper_analyses: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build a novelty database from paper analyses."""
        papers = []
        if isinstance(paper_analyses, list):
            papers = paper_analyses
        elif isinstance(paper_analyses, dict):
            papers = paper_analyses.get("papers", paper_analyses.get("analyses", []))

        db: List[Dict[str, Any]] = []
        for p in papers:
            if not isinstance(p, dict):
                continue
            db.append({
                "title": p.get("title", p.get("paper_id", "")),
                "abstract": p.get("abstract", p.get("summary", "")),
                "method": p.get("methodology", p.get("method", "")),
            })
        return db

    def _write_minimal_gap_analysis(
        self,
        path: str,
        gap_candidates: Dict[str, Any],
        research_context: Dict[str, Any],
    ) -> None:
        gaps = gap_candidates.get("gaps", [])
        lines = [
            "# Research Gap Analysis",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Identified Gaps",
            "",
        ]
        for i, gap in enumerate(gaps, 1):
            lines.append(f"{i}. **{gap.get('gap_type', 'unspecified')}**: {gap.get('description', '')}")
        if not gaps:
            lines.append("1. No specific gaps identified.")
        lines.extend([
            "",
            "## Existing Methods",
            "",
        ])
        for m in research_context.get("existing_methods", []):
            lines.append(f"- {m}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _build_innovation_candidates(
        self,
        innovations: List[Dict[str, Any]],
        novelty_reports: List[Dict[str, Any]],
        gap_candidates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build innovation_candidates.json conforming to schema."""
        gaps = gap_candidates.get("gaps", [])
        candidates: List[Dict[str, Any]] = []

        for i, inn in enumerate(innovations):
            novelty_report = novelty_reports[i] if i < len(novelty_reports) else {}
            evaluation = inn.get("evaluation", {})

            source_gap = ""
            if i < len(gaps):
                source_gap = gaps[i].get("description", "")

            candidates.append({
                "title": inn.get("new_hypothesis", f"Innovation {i+1}")[:200],
                "description": inn.get("difference_from_existing", inn.get("expected_contribution", "")),
                "novelty_score": float(evaluation.get("novelty", novelty_report.get("novelty_score", 0.0))),
                "feasibility_score": float(evaluation.get("feasibility", 0.0)),
                "impact_score": float(evaluation.get("publication_potential", 0.0)),
                "source_gap": source_gap,
                # Extra metadata (not required by schema but useful).
                "innovation_id": inn.get("innovation_id", f"inn_{i+1}"),
                "root_cause": inn.get("root_cause", ""),
                "existing_work": inn.get("existing_work", ""),
                "novelty_level": novelty_report.get("novelty_level", "unknown"),
                "generation_method": inn.get("generation_method", "rule_based"),
            })

        if not candidates:
            candidates.append({
                "title": "No innovations generated",
                "description": "Innovation generation did not produce candidates.",
                "novelty_score": 0.0,
                "feasibility_score": 0.0,
                "impact_score": 0.0,
                "source_gap": "",
            })

        return {"candidates": candidates}

    def _build_novelty_analysis_md(
        self,
        innovations: List[Dict[str, Any]],
        novelty_reports: List[Dict[str, Any]],
        causal_result: Dict[str, Any],
    ) -> str:
        lines = [
            "# Novelty Analysis",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Causal Analysis Summary",
            "",
        ]
        if causal_result:
            root_causes = causal_result.get("root_causes", [])
            if isinstance(root_causes, list):
                for rc in root_causes:
                    if isinstance(rc, dict):
                        lines.append(f"- {rc.get('description', rc)}")
                    else:
                        lines.append(f"- {rc}")
            lines.append(f"  - Confidence: {causal_result.get('confidence', 'N/A')}")
            lines.append(f"  - Chain depth: {causal_result.get('chain_depth', 'N/A')}")
        else:
            lines.append("No causal analysis available.")

        lines.extend(["", "## Innovation Novelty Assessment", ""])
        for i, (inn, report) in enumerate(zip(innovations, novelty_reports)):
            lines.append(f"### Innovation {i+1}: {inn.get('new_hypothesis', 'N/A')[:100]}")
            lines.append("")
            lines.append(f"- **Novelty Score:** {report.get('novelty_score', 'N/A')}")
            lines.append(f"- **Novelty Level:** {report.get('novelty_level', 'N/A')}")
            lines.append(f"- **Database Size:** {report.get('database_size', 'N/A')}")

            similar = report.get("similar_works", [])
            if similar:
                lines.append("- **Similar Works:**")
                for sw in similar[:5]:
                    if isinstance(sw, dict):
                        lines.append(f"  - {sw.get('title', sw)}")
                    else:
                        lines.append(f"  - {sw}")
            else:
                lines.append("- **Similar Works:** None found")

            summary = report.get("check_summary", "")
            if summary:
                lines.append(f"- **Summary:** {summary}")
            lines.append("")

        return "\n".join(lines)

    def _build_final_direction_md(
        self,
        innovations: List[Dict[str, Any]],
        novelty_reports: List[Dict[str, Any]],
        causal_result: Dict[str, Any],
        hypothesis_path: str,
    ) -> str:
        # Select best innovation by overall novelty score.
        best_inn: Optional[Dict[str, Any]] = None
        best_score = -1.0
        best_report: Dict[str, Any] = {}
        for inn, report in zip(innovations, novelty_reports):
            score = float(report.get("novelty_score", 0.0))
            if score > best_score:
                best_score = score
                best_inn = inn
                best_report = report

        # Read hypothesis content if available.
        hypothesis_content = ""
        if hypothesis_path and os.path.exists(hypothesis_path):
            try:
                with open(hypothesis_path, "r", encoding="utf-8") as f:
                    hypothesis_content = f.read()
            except Exception:
                hypothesis_content = ""

        lines = [
            "# Final Research Direction",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Selected Direction",
            "",
        ]

        if best_inn:
            lines.append(f"**{best_inn.get('new_hypothesis', 'N/A')}**")
            lines.append("")
            lines.append("## Justification")
            lines.append("")
            lines.append(
                best_inn.get("difference_from_existing", "No justification available.")
            )
            lines.append("")
            lines.append("## Novelty Argument")
            lines.append("")
            novelty_arg = best_report.get("check_summary", "No novelty assessment available.")
            lines.append(novelty_arg)
            lines.append(f"\nNovelty score: {best_report.get('novelty_score', 'N/A')}")
            lines.append(f"Novelty level: {best_report.get('novelty_level', 'N/A')}")
            lines.append("")
            lines.append("## Feasibility Assessment")
            lines.append("")
            evaluation = best_inn.get("evaluation", {})
            lines.append(f"- Feasibility score: {evaluation.get('feasibility', 'N/A')}")
            lines.append(f"- Technical difference: {evaluation.get('technical_difference', 'N/A')}")
            lines.append(f"- Theoretical depth: {evaluation.get('theoretical_depth', 'N/A')}")
            lines.append("")
            lines.append("## Expected Contribution")
            lines.append("")
            lines.append(
                best_inn.get("expected_contribution", "No expected contribution specified.")
            )
        else:
            lines.append("No innovation candidates were generated.")
            lines.append("")
            lines.append("## Justification")
            lines.append("")
            lines.append("Innovation generation did not produce candidates.")

        # Include causal analysis context.
        if causal_result:
            lines.extend([
                "",
                "## Causal Analysis Context",
                "",
                f"- Observation: {causal_result.get('observation', 'N/A')}",
                f"- Root causes: {causal_result.get('root_causes', [])}",
                f"- Confidence: {causal_result.get('confidence', 'N/A')}",
            ])

        # Include hypothesis excerpt if available.
        if hypothesis_content:
            lines.extend([
                "",
                "## Generated Hypotheses (excerpt)",
                "",
                hypothesis_content[:2000],
            ])

        return "\n".join(lines)
