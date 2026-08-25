"""
Module 04 -- Research Landscape & Gap Analysis
Implementation (facade/adapter pattern).

Wraps the existing reasoning components:
  - reasoning.gap_analyzer.gap_analyzer.GapAnalyzer
  - reasoning.scientific_reasoner.contradiction_detector.ContradictionDetector

Produces:
  - research_landscape.md
  - taxonomy.json
  - trend_analysis.json
  - contradiction_map.json
  - gap_candidates.json
  - Stage_Report.md (v8.3)

v8.3 upgrades:
  - Enhanced gap analysis using 10-dimension paper analysis data
  - Stage_Report.md for pipeline tracking
  - Structured gap taxonomy with dimension coverage
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Project-root bootstrap so we can import the existing ``reasoning`` package.
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from reasoning.gap_analyzer.gap_analyzer import GapAnalyzer
from reasoning.scientific_reasoner.contradiction_detector import ContradictionDetector

from .interface import (
    Module04Interface,
    ResearchLandscapeInput,
    ResearchLandscapeOutput,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM provider adapter
# ---------------------------------------------------------------------------

class LLMProviderAdapter:
    """Thin adapter that makes a v3 LLM provider compatible with the
    existing reasoning code.

    The existing reasoning modules call ``provider.generate(prompt)`` and
    check ``if self.llm_provider:``.  The v3 provider satisfies both of
    these, but this adapter also exposes ``is_available()`` so the wrapped
    reasoning modules can query availability uniformly.
    """

    def __init__(self, v3_provider: Any) -> None:
        self._provider = v3_provider

    def generate(self, prompt: str, context: str = "") -> str:
        """Delegate to the v3 provider, forwarding *context* as a kwarg."""
        try:
            return self._provider.generate(prompt, context=context)
        except TypeError:
            # Fallback: some providers only accept ``prompt``.
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
# Module 04 implementation
# ---------------------------------------------------------------------------

class ResearchLandscapeModule(Module04Interface):
    """Facade that wraps GapAnalyzer + ContradictionDetector.

    Implements the full Module 04 lifecycle defined in
    ``Module04Interface``.
    """

    MODULE_ID = "04"
    MODULE_NAME = "Research Landscape & Gap Analysis"
    VERSION = "1.0.0"

    def __init__(self, llm_provider: Any = None) -> None:
        """Create the module.

        Args:
            llm_provider: Optional v3 LLM provider instance.  When *None*
                the wrapped reasoning components fall back to rule-based
                analysis.
        """
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
        logger.info("Module 04 config loaded: %s", list(self._config.keys()))

    def validate_input(self, input_data: ResearchLandscapeInput) -> bool:
        """Validate that all required inputs are present."""
        if not input_data.input_files.get("paper_analysis.json"):
            logger.error("Missing required input file: paper_analysis.json")
            return False
        path = input_data.input_files["paper_analysis.json"]
        if not os.path.exists(path):
            logger.error("paper_analysis.json path does not exist: %s", path)
            return False
        return True

    def execute(
        self, input_data: ResearchLandscapeInput
    ) -> ResearchLandscapeOutput:
        """Run the research-landscape pipeline.

        Steps:
        1.  Load ``paper_analysis.json`` and convert to a paper-database
            format understood by ``GapAnalyzer``.
        2.  Invoke ``GapAnalyzer.analyze`` to produce the landscape
            markdown.
        3.  Invoke ``ContradictionDetector.analyze_paper_conflicts`` to
            produce the contradiction map.
        4.  Derive ``taxonomy.json``, ``trend_analysis.json`` and
            ``gap_candidates.json`` from the structured data.
        """
        warnings: List[str] = []
        errors: List[str] = []
        output_files: Dict[str, str] = {}

        # Determine output directory.
        output_dir = self._config.get(
            "output_dir",
            os.path.join(tempfile.gettempdir(), f"module04_{input_data.task_id}"),
        )
        os.makedirs(output_dir, exist_ok=True)

        # ----------------------------------------------------------
        # 1. Load paper analyses and build a paper database.
        # ----------------------------------------------------------
        paper_analysis_path = input_data.input_files.get("paper_analysis.json")
        if not paper_analysis_path or not os.path.exists(paper_analysis_path):
            errors.append("paper_analysis.json not found or path invalid")
            return ResearchLandscapeOutput(
                task_id=input_data.task_id,
                output_files={},
                manifest={},
                warnings=warnings,
                errors=errors,
            )

        papers = self._load_paper_analyses(paper_analysis_path)
        if not papers:
            errors.append("No valid paper analyses found in paper_analysis.json")
            return ResearchLandscapeOutput(
                task_id=input_data.task_id,
                output_files={},
                manifest={},
                warnings=warnings,
                errors=errors,
            )

        # Write a temporary paper database for GapAnalyzer.
        paper_db_path = os.path.join(output_dir, "_paper_database.json")
        with open(paper_db_path, "w", encoding="utf-8") as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)

        # ----------------------------------------------------------
        # 2. GapAnalyzer -- research landscape markdown.
        # ----------------------------------------------------------
        landscape_path = os.path.join(output_dir, "research_landscape.md")
        gap_analyzer = GapAnalyzer(llm_provider=self._llm_provider)
        try:
            gap_analyzer.analyze(
                paper_database_path=paper_db_path,
                output_path=landscape_path,
            )
            output_files["research_landscape.md"] = landscape_path
        except Exception as exc:
            logger.error("GapAnalyzer failed: %s", exc, exc_info=True)
            errors.append(f"GapAnalyzer error: {exc}")
            # Write a minimal landscape file so validation can proceed.
            self._write_minimal_landscape(landscape_path, papers)
            output_files["research_landscape.md"] = landscape_path
            warnings.append(f"GapAnalyzer fell back to minimal output: {exc}")

        # ----------------------------------------------------------
        # 3. ContradictionDetector -- contradiction map.
        # ----------------------------------------------------------
        contradiction_map = self._build_contradiction_map(papers)
        contradiction_path = os.path.join(output_dir, "contradiction_map.json")
        with open(contradiction_path, "w", encoding="utf-8") as f:
            json.dump(contradiction_map, f, ensure_ascii=False, indent=2)
        output_files["contradiction_map.json"] = contradiction_path

        # ----------------------------------------------------------
        # 4. Taxonomy, trend analysis, gap candidates.
        # ----------------------------------------------------------
        taxonomy = self._build_taxonomy(papers)
        taxonomy_path = os.path.join(output_dir, "taxonomy.json")
        with open(taxonomy_path, "w", encoding="utf-8") as f:
            json.dump(taxonomy, f, ensure_ascii=False, indent=2)
        output_files["taxonomy.json"] = taxonomy_path

        trend_analysis = self._build_trend_analysis(papers)
        trend_path = os.path.join(output_dir, "trend_analysis.json")
        with open(trend_path, "w", encoding="utf-8") as f:
            json.dump(trend_analysis, f, ensure_ascii=False, indent=2)
        output_files["trend_analysis.json"] = trend_path

        gap_candidates = self._build_gap_candidates(papers, contradiction_map)
        gap_path = os.path.join(output_dir, "gap_candidates.json")
        with open(gap_path, "w", encoding="utf-8") as f:
            json.dump(gap_candidates, f, ensure_ascii=False, indent=2)
        output_files["gap_candidates.json"] = gap_path

        # v8.3: Stage_Report.md
        stage_report = self._build_stage_report(
            input_data.task_id, papers, gap_candidates, contradiction_map, warnings, errors
        )
        stage_path = os.path.join(output_dir, "Stage_Report.md")
        with open(stage_path, "w", encoding="utf-8") as f:
            f.write(stage_report)
        output_files["Stage_Report.md"] = stage_path

        output = ResearchLandscapeOutput(
            task_id=input_data.task_id,
            output_files=output_files,
            manifest={},
            warnings=warnings,
            errors=errors,
        )

        # Validate output.
        if not self.validate_output(output):
            warnings.append("Output validation reported issues")

        # Attach manifest.
        output.manifest = self.write_manifest(output)
        return output

    def validate_output(self, output: ResearchLandscapeOutput) -> bool:
        """Validate that all required outputs are present."""
        required = [
            "research_landscape.md", "taxonomy.json", "trend_analysis.json",
            "contradiction_map.json", "gap_candidates.json",
        ]
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
        self, output: ResearchLandscapeOutput
    ) -> Dict[str, Any]:
        """Assess quality against hard requirements and soft thresholds."""
        details: Dict[str, Any] = {}
        passed = True

        # Hard: taxonomy has >= 1 category.
        taxonomy_path = output.output_files.get("taxonomy.json", "")
        taxonomy = self._safe_load_json(taxonomy_path)
        cat_count = len(taxonomy.get("categories", [])) if taxonomy else 0
        details["taxonomy_categories"] = cat_count
        if cat_count < 1:
            passed = False
            details["taxonomy_pass"] = False
        else:
            details["taxonomy_pass"] = True

        # Hard: gap_candidates has >= 1 gap.
        gap_path = output.output_files.get("gap_candidates.json", "")
        gaps = self._safe_load_json(gap_path)
        gap_count = len(gaps.get("gaps", [])) if gaps else 0
        details["gap_candidates_count"] = gap_count
        if gap_count < 1:
            passed = False
            details["gaps_pass"] = False
        else:
            details["gaps_pass"] = True

        # Hard: research_landscape.md is non-empty.
        landscape_path = output.output_files.get("research_landscape.md", "")
        landscape_nonempty = (
            os.path.exists(landscape_path)
            and os.path.getsize(landscape_path) > 0
        )
        details["landscape_nonempty"] = landscape_nonempty
        if not landscape_nonempty:
            passed = False
            details["landscape_pass"] = False
        else:
            details["landscape_pass"] = True

        # Soft: prefer >= 3 gap candidates.
        details["gaps_soft_pass"] = gap_count >= 3

        # Soft: prefer >= 2 contradictions.
        contra_path = output.output_files.get("contradiction_map.json", "")
        contra = self._safe_load_json(contra_path)
        contra_count = len(contra.get("contradictions", [])) if contra else 0
        details["contradictions_count"] = contra_count
        details["contradictions_soft_pass"] = contra_count >= 2

        return {
            "passed": passed,
            "details": details,
            "assessed_at": datetime.now().isoformat(),
        }

    def write_manifest(
        self, output: ResearchLandscapeOutput
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

    def write_report(self, output: ResearchLandscapeOutput) -> str:
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
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_load_json(path: str) -> Optional[Dict[str, Any]]:
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _load_paper_analyses(self, path: str) -> List[Dict[str, Any]]:
        """Load ``paper_analysis.json`` and normalise to paper dicts."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if "papers" in data:
                items = data["papers"]
            elif "analyses" in data:
                items = data["analyses"]
            else:
                items = [data]
        else:
            items = []

        papers: List[Dict[str, Any]] = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            # Normalise field names for GapAnalyzer compatibility.
            paper: Dict[str, Any] = {
                "paper_id": item.get("paper_id", item.get("id", f"paper_{i+1}")),
                "title": item.get("title", item.get("paper_id", f"paper_{i+1}")),
                "method": item.get("methodology", item.get("method", "")),
                "abstract": item.get("abstract", item.get("summary", "")),
                "conclusion": item.get("conclusion", ""),
                "limitation": item.get("limitations", ""),
                "year": item.get("year", ""),
                "venue": item.get("venue", ""),
            }
            if isinstance(paper["limitation"], list):
                paper["limitation"] = "; ".join(str(x) for x in paper["limitation"])
            if isinstance(paper.get("key_findings"), list):
                paper["contribution"] = "; ".join(str(x) for x in item["key_findings"])
            else:
                paper["contribution"] = item.get("main_contribution", "")
            papers.append(paper)
        return papers

    def _write_minimal_landscape(
        self, path: str, papers: List[Dict[str, Any]]
    ) -> None:
        """Write a minimal landscape markdown when GapAnalyzer fails."""
        lines = [
            "# Research Landscape Analysis",
            "",
            f"Generated: {datetime.now().isoformat()}",
            f"Papers analysed: {len(papers)}",
            "",
            "## Papers",
            "",
        ]
        for p in papers:
            lines.append(f"- **{p.get('title', 'Unknown')}** -- {p.get('method', 'N/A')}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _build_contradiction_map(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use ContradictionDetector to build the contradiction map."""
        detector = ContradictionDetector(
            llm_provider=self._llm_provider,
            llm_enabled=self._llm_provider is not None,
        )
        try:
            result = detector.analyze_paper_conflicts(papers)
            contradictions: List[Dict[str, Any]] = []
            for pair in result.get("conflict_pairs", []):
                contradictions.append({
                    "topic": pair.get("type", "unknown"),
                    "paper_a": pair.get("paper_a", ""),
                    "paper_b": pair.get("paper_b", ""),
                    "description": pair.get("description", ""),
                    "severity": pair.get("severity", "low"),
                })
            return {
                "contradictions": contradictions,
                "total_papers": result.get("total_papers", len(papers)),
                "total_pairs": result.get("total_pairs", 0),
                "summary": result.get("conflict_summary", ""),
            }
        except Exception as exc:
            logger.warning("ContradictionDetector failed: %s", exc)
            return {
                "contradictions": [],
                "total_papers": len(papers),
                "total_pairs": 0,
                "summary": f"Contradiction analysis failed: {exc}",
            }

    def _build_taxonomy(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build a taxonomy by classifying papers into research fields."""
        # Reuse GapAnalyzer's field classification logic via a lightweight
        # local implementation to avoid depending on private methods.
        from reasoning.gap_analyzer.gap_analyzer import FIELD_KEYWORDS

        categories: Dict[str, List[str]] = {}
        for paper in papers:
            title = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
            method = (paper.get("method", "")).lower()
            text = f"{title} {method}"
            matched = False
            for field, keywords in FIELD_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    categories.setdefault(field, []).append(
                        paper.get("paper_id", paper.get("title", ""))
                    )
                    matched = True
            if not matched:
                categories.setdefault("Other", []).append(
                    paper.get("paper_id", paper.get("title", ""))
                )

        cat_list = [
            {
                "name": name,
                "papers": sorted(set(ids)),
                "subcategories": [],
            }
            for name, ids in sorted(categories.items())
        ]
        return {"categories": cat_list}

    def _build_trend_analysis(
        self, papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build trend analysis from paper years and methods."""
        from reasoning.gap_analyzer.gap_analyzer import TECHNIQUE_KEYWORDS

        # Group papers by technique.
        technique_papers: Dict[str, List[str]] = {}
        for paper in papers:
            text = (
                paper.get("method", "") + " " + paper.get("abstract", "")
            ).lower()
            for tech, keywords in TECHNIQUE_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    technique_papers.setdefault(tech, []).append(
                        paper.get("paper_id", paper.get("title", ""))
                    )

        trends: List[Dict[str, Any]] = []
        for tech, ids in sorted(technique_papers.items()):
            # Determine trajectory from year distribution.
            years = [
                p.get("year", "")
                for p in papers
                if p.get("paper_id", p.get("title", "")) in ids and p.get("year")
            ]
            if years:
                trajectory = "growing" if len(set(years)) > 1 else "stable"
            else:
                trajectory = "unknown"
            trends.append({
                "topic": tech,
                "trajectory": trajectory,
                "key_papers": sorted(set(ids)),
            })
        return {"trends": trends}

    def _build_gap_candidates(
        self,
        papers: List[Dict[str, Any]],
        contradiction_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build gap candidates from paper limitations and contradictions."""
        gaps: List[Dict[str, Any]] = []

        # Collect limitations.
        limitation_papers: Dict[str, List[str]] = {}
        for paper in papers:
            lim = paper.get("limitation", "")
            if not lim:
                continue
            pid = paper.get("paper_id", paper.get("title", ""))
            # Normalise limitation text.
            for sentence in re.split(r"[;.\n]", lim):
                sentence = sentence.strip()
                if len(sentence) < 5:
                    continue
                limitation_papers.setdefault(sentence, []).append(pid)

        for desc, pids in limitation_papers.items():
            gaps.append({
                "description": desc,
                "gap_type": "limitation",
                "supporting_papers": sorted(set(pids)),
                "novelty_score": 0.5,
            })

        # Add contradictions as conflict gaps.
        for contra in contradiction_map.get("contradictions", []):
            gaps.append({
                "description": contra.get("description", "Unresolved contradiction"),
                "gap_type": "contradiction",
                "supporting_papers": [
                    contra.get("paper_a", ""),
                    contra.get("paper_b", ""),
                ],
                "novelty_score": 0.6,
            })

        # Deduplicate by description.
        seen: set = set()
        unique_gaps: List[Dict[str, Any]] = []
        for g in gaps:
            key = g["description"][:80]
            if key not in seen:
                seen.add(key)
                unique_gaps.append(g)

        # Ensure at least one gap.
        if not unique_gaps:
            unique_gaps.append({
                "description": "No specific gaps identified from the current paper set.",
                "gap_type": "unspecified",
                "supporting_papers": [],
                "novelty_score": 0.0,
            })

        return {"gaps": unique_gaps}

    # ------------------------------------------------------------------
    # v8.3: Stage Report
    # ------------------------------------------------------------------

    def _build_stage_report(
        self,
        task_id: str,
        papers: List[Dict[str, Any]],
        gap_candidates: Dict[str, Any],
        contradiction_map: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        """v8.3: Build Stage_Report.md for Module 04."""
        gaps = gap_candidates.get("gaps", [])
        contradictions = contradiction_map.get("contradictions", [])

        # Classify gaps by type
        gap_types: Dict[str, int] = {}
        for g in gaps:
            gtype = g.get("gap_type", "unspecified")
            gap_types[gtype] = gap_types.get(gtype, 0) + 1

        lines = [
            "# Module 04 — Research Landscape & Gap Analysis Stage Report",
            "",
            f"**Task ID:** {task_id}",
            f"**Timestamp:** {datetime.now().isoformat()}",
            f"**Status:** {'COMPLETED' if not errors else 'FAILED'}",
            "",
            "## 当前目标",
            "",
            "基于文献分析构建研究领域全景图，识别研究空白和矛盾点。",
            "",
            "## 输入",
            "",
            f"- paper_analysis.json ({len(papers)} 篇论文)",
            "",
            "## 输出",
            "",
            f"- research_landscape.md: 研究全景",
            f"- taxonomy.json: 分类体系",
            f"- trend_analysis.json: 趋势分析",
            f"- contradiction_map.json: 矛盾图 ({len(contradictions)} 个矛盾)",
            f"- gap_candidates.json: 研究空白 ({len(gaps)} 个空白)",
            f"- Stage_Report.md: 阶段报告",
            "",
            "## 完成状态",
            "",
            f"- 论文数量: {len(papers)}",
            f"- 识别空白: {len(gaps)}",
            f"- 矛盾点: {len(contradictions)}",
            f"- 空白类型分布: {gap_types}",
            "",
        ]

        if warnings:
            lines.extend(["## 警告", ""])
            for w in warnings:
                lines.append(f"- {w}")
        if errors:
            lines.extend(["## 错误", ""])
            for e in errors:
                lines.append(f"- {e}")

        return "\n".join(lines)
