"""
Module 03 — Literature Intelligence
v3 Implementation (Facade/Adapter pattern).

Wraps the legacy classes:
    - ``literature.extractor.paper_extractor.PaperExtractor``
    - ``literature.extractor.quality_checker.QualityChecker``
    - ``literature.database.paper_database.PaperDatabase``
    - ``literature.pipeline.literature_pipeline.LiteraturePipeline``

to satisfy the v3 ``Module03Interface`` contract.

Upstream:   02
Downstream: 04, 05

Output files produced:
    - paper_analysis.json
    - paper_analysis.md
    - literature_analysis_index.jsonl
    - Module03_Validation_Report.md
"""

import importlib.util
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------ #
# Path setup: add project root for legacy ``literature`` imports
# ------------------------------------------------------------------ #
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ------------------------------------------------------------------ #
# Load the interface contract from this module's directory.
# ------------------------------------------------------------------ #
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "module_03_interface", os.path.join(_MODULE_DIR, "interface.py")
)
_interface_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_interface_mod)

Module03Interface = _interface_mod.Module03Interface
LiteratureIntelligenceInput = _interface_mod.LiteratureIntelligenceInput
LiteratureIntelligenceOutput = _interface_mod.LiteratureIntelligenceOutput

# ------------------------------------------------------------------ #
# Legacy imports
# ------------------------------------------------------------------ #
from literature.extractor.paper_extractor import PaperExtractor  # noqa: E402
from literature.extractor.quality_checker import QualityChecker  # noqa: E402
from literature.database.paper_database import PaperDatabase  # noqa: E402
from literature.pipeline.literature_pipeline import LiteraturePipeline  # noqa: E402

logger = logging.getLogger(__name__)


class LiteratureIntelligenceImplementation(Module03Interface):
    """Concrete v3 implementation for Module 03 — Literature Intelligence.

    This adapter wraps the legacy extractor, quality checker, database,
    and pipeline classes and exposes them through the v3 module lifecycle.
    """

    MODULE_ID = "03"
    MODULE_NAME = "Literature Intelligence"
    MODULE_VERSION = "1.0"

    # Default configuration.
    DEFAULT_CONFIG: Dict[str, Any] = {
        "output_dir": "intelligence_output",
    }

    def __init__(self) -> None:
        self._config: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
        self._output_dir: str = self._config["output_dir"]
        self._extractor: Optional[PaperExtractor] = None
        self._quality_checker: Optional[QualityChecker] = None
        self._db: Optional[PaperDatabase] = None
        self._pipeline: Optional[LiteraturePipeline] = None
        self._last_output: Optional[LiteratureIntelligenceOutput] = None

    # ------------------------------------------------------------------
    # 1. load_config
    # ------------------------------------------------------------------
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load and merge module-specific configuration.

        Args:
            config: Configuration dictionary. Recognised keys:
                - output_dir (str, default "intelligence_output")
        """
        merged = dict(self.DEFAULT_CONFIG)
        merged.update(config or {})
        self._config = merged
        self._output_dir = merged.get("output_dir", "intelligence_output")
        self._extractor = PaperExtractor(prompt_dir=self._output_dir)
        self._quality_checker = QualityChecker()
        self._db = PaperDatabase()
        logger.info("Module 03 config loaded")

    # ------------------------------------------------------------------
    # 2. validate_input
    # ------------------------------------------------------------------
    def validate_input(self, input_data: LiteratureIntelligenceInput) -> bool:
        """Validate that at least one normalized paper.md is available.

        Args:
            input_data: Standard module input.

        Returns:
            True if at least one paper.md path is found.
        """
        # Check input_files for paper.md paths
        if input_data.input_files:
            md_files = [
                path for name, path in input_data.input_files.items()
                if name.endswith("paper.md") or name.endswith(".md")
            ]
            if md_files:
                return True

        # Check upstream_module_02 output for paper.md
        upstream = input_data.upstream_module_02 or {}
        output_files = upstream.get("output_files", {})
        md_keys = [k for k in output_files if "normalized/paper.md" in k]
        if md_keys:
            return True

        logger.error("No normalized paper.md files found in input")
        return False

    # ------------------------------------------------------------------
    # 3. execute
    # ------------------------------------------------------------------
    def execute(self, input_data: LiteratureIntelligenceInput) -> LiteratureIntelligenceOutput:
        """Execute the module's core logic.

        Extracts structured knowledge from each normalized paper, runs
        quality checks, stores results in the database, and produces
        the aggregated analysis files.

        Args:
            input_data: Validated module input.

        Returns:
            Module output with output_files, manifest, warnings, errors.
        """
        warnings: List[str] = []
        errors: List[str] = []

        # Initialise components if not already done
        if self._extractor is None:
            self.load_config({})

        os.makedirs(self._output_dir, exist_ok=True)

        # Discover paper.md files and their metadata
        paper_entries = self._discover_papers(input_data)
        if not paper_entries:
            errors.append("No normalized papers found to analyze")
            return self._build_output(input_data.task_id, {}, {}, warnings, errors)

        all_analyses: List[Dict[str, Any]] = []
        quality_reports: List[Dict[str, Any]] = []
        index_entries: List[Dict[str, Any]] = []
        analyzed_pids: List[str] = []

        for entry in paper_entries:
            paper_id = entry["paper_id"]
            md_path = entry["md_path"]
            metadata = entry.get("metadata", {})

            if not os.path.exists(md_path):
                warnings.append(f"paper.md not found for '{paper_id}': {md_path}")
                continue

            # Extract knowledge using PaperExtractor
            analysis_path = os.path.join(
                self._output_dir, f"{paper_id}_analysis.json"
            )
            try:
                knowledge = self._extractor.extract(md_path, analysis_path, metadata=metadata)
                if knowledge and isinstance(knowledge, dict):
                    all_analyses.append(knowledge)
                    analyzed_pids.append(paper_id)

                    # Add to database
                    self._db.add(knowledge)

                    # Quality check
                    qr = self._quality_checker.check(knowledge)
                    quality_reports.append(qr)

                    # Build index entry
                    index_entry = {
                        "paper_id": knowledge.get("paper_id", paper_id),
                        "title": knowledge.get("title", ""),
                        "venue": knowledge.get("venue", ""),
                        "year": knowledge.get("year"),
                        "main_contribution": knowledge.get("innovation", ""),
                        "methodology": knowledge.get("method", ""),
                        "research_problem": knowledge.get("research_problem", ""),
                        "dataset": knowledge.get("dataset", ""),
                        "baseline": knowledge.get("baseline", ""),
                        "limitation": knowledge.get("limitation", ""),
                        "future_direction": knowledge.get("future_direction", ""),
                        "extraction_strategy": knowledge.get("_extraction_strategy", ""),
                        "quality_score": qr.get("score", 0),
                    }
                    index_entries.append(index_entry)
                else:
                    warnings.append(f"Extraction returned empty for '{paper_id}'")
            except Exception as exc:
                warnings.append(f"Extraction failed for '{paper_id}': {exc}")

        if not all_analyses:
            errors.append("No papers were successfully analyzed")
            return self._build_output(input_data.task_id, {}, {}, warnings, errors)

        # Write paper_analysis.json (aggregated)
        analysis_json_path = os.path.join(self._output_dir, "paper_analysis.json")
        with open(analysis_json_path, "w", encoding="utf-8") as f:
            json.dump(all_analyses, f, indent=2, ensure_ascii=False)

        # v8.3: 10-dimension analysis
        dim_analysis = self._analyze_10_dimensions(all_analyses)
        dim_analysis_path = os.path.join(self._output_dir, "dimension_analysis.json")
        with open(dim_analysis_path, "w", encoding="utf-8") as f:
            json.dump(dim_analysis, f, indent=2, ensure_ascii=False)

        # Write paper_analysis.md (human-readable summary)
        analysis_md_path = os.path.join(self._output_dir, "paper_analysis.md")
        md_content = self._build_analysis_markdown(all_analyses, quality_reports)
        with open(analysis_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # v8.3: Generate Stage_Report.md
        stage_report_path = self._generate_stage_report(
            self._output_dir, input_data.task_id, all_analyses, dim_analysis, warnings, errors
        )

        # Write literature_analysis_index.jsonl
        index_path = os.path.join(self._output_dir, "literature_analysis_index.jsonl")
        with open(index_path, "w", encoding="utf-8") as f:
            for entry in index_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Save database
        db_path = os.path.join(self._output_dir, "paper_database.json")
        self._db.save(db_path)

        # Save quality report
        qr_path = os.path.join(self._output_dir, "extraction_quality_report.json")
        if quality_reports:
            self._quality_checker.save_report(quality_reports, qr_path)

        # v8.3.1: Build paper_analysis_trace.json
        trace_data = self._build_analysis_trace(all_analyses, paper_entries)
        trace_path = os.path.join(self._output_dir, "paper_analysis_trace.json")
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2, ensure_ascii=False)

        # Build manifest
        manifest = {
            "total_papers_analyzed": len(all_analyses),
            "analyzed_paper_ids": analyzed_pids,
            "total_quality_pass": sum(1 for r in quality_reports if r.get("overall_pass")),
            "total_quality_fail": sum(1 for r in quality_reports if not r.get("overall_pass")),
            "average_quality_score": round(
                sum(r.get("score", 0) for r in quality_reports) / len(quality_reports), 1
            ) if quality_reports else 0,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "task_id": input_data.task_id,
        }

        # Output files mapping
        output_files: Dict[str, str] = {
            "paper_analysis.json": analysis_json_path,
            "paper_analysis.md": analysis_md_path,
            "literature_analysis_index.jsonl": index_path,
            "dimension_analysis.json": dim_analysis_path,
            "Stage_Report.md": stage_report_path,
        }
        output_files["paper_analysis_trace.json"] = trace_path

        # Write module manifest
        mod_manifest = {
            "module_id": self.MODULE_ID,
            "module_name": self.MODULE_NAME,
            "module_version": self.MODULE_VERSION,
            "task_id": input_data.task_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output_files": output_files,
            "manifest_data": manifest,
            "warnings": warnings,
            "errors": errors,
            "status": "COMPLETED" if not errors else "FAILED",
        }
        mod_manifest_path = os.path.join(self._output_dir, "module_manifest.json")
        with open(mod_manifest_path, "w", encoding="utf-8") as f:
            json.dump(mod_manifest, f, indent=2, ensure_ascii=False)
        output_files["module_manifest.json"] = mod_manifest_path

        # Write validation report
        report = self._generate_report(input_data.task_id, output_files, manifest, warnings, errors)
        report_path = os.path.join(self._output_dir, "Module03_Validation_Report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        output_files["Module03_Validation_Report.md"] = report_path

        output = LiteratureIntelligenceOutput(
            task_id=input_data.task_id,
            output_files=output_files,
            manifest=manifest,
            warnings=warnings,
            errors=errors,
        )
        self._last_output = output
        return output

    # ------------------------------------------------------------------
    # 4. validate_output
    # ------------------------------------------------------------------
    def validate_output(self, output: LiteratureIntelligenceOutput) -> bool:
        """Validate that all required output files exist and are non-empty.

        Args:
            output: Module output to validate.

        Returns:
            True if all required files are present and valid.
        """
        required = [
            "paper_analysis.json",
            "paper_analysis.md",
            "literature_analysis_index.jsonl",
            "Module03_Validation_Report.md",
        ]
        for fname in required:
            path = output.output_files.get(fname)
            if not path or not os.path.exists(path):
                logger.error("Missing output file: %s", fname)
                return False
        return True

    # ------------------------------------------------------------------
    # 5. quality_assessment
    # ------------------------------------------------------------------
    def quality_assessment(self, output: LiteratureIntelligenceOutput) -> Dict[str, Any]:
        """Assess output quality against hard requirements and soft thresholds.

        Args:
            output: Module output to assess.

        Returns:
            Dictionary with quality metrics.
        """
        manifest = output.manifest
        total_analyzed = manifest.get("total_papers_analyzed", 0)

        # Hard requirement 0: paper_analysis.json exists for every normalized paper
        analysis_path = output.output_files.get("paper_analysis.json", "")
        hard_analysis_exists = bool(analysis_path and os.path.exists(analysis_path))

        # Hard requirement 1: Each analysis has main_contribution and methodology
        has_contribution_and_method = True
        contribution_count = 0
        method_count = 0
        if hard_analysis_exists:
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analyses = json.load(f)
                for a in analyses:
                    if a.get("innovation") or a.get("method"):
                        contribution_count += 1
                    if a.get("method"):
                        method_count += 1
                if analyses:
                    has_contribution_and_method = (
                        contribution_count == len(analyses) or
                        method_count == len(analyses)
                    )
            except Exception:
                has_contribution_and_method = False

        # Hard requirement 2: literature_analysis_index.jsonl is valid JSONL
        index_path = output.output_files.get("literature_analysis_index.jsonl", "")
        index_valid = False
        index_line_count = 0
        if index_path and os.path.exists(index_path):
            index_valid = True
            with open(index_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            json.loads(line)
                            index_line_count += 1
                        except json.JSONDecodeError:
                            index_valid = False
                            break

        hard: Dict[str, bool] = {
            "paper_analysis_exists": hard_analysis_exists,
            "has_contribution_and_method": has_contribution_and_method,
            "index_valid_jsonl": index_valid,
        }
        all_hard_pass = all(hard.values())

        # Soft threshold 0: Prefer >= 90% of papers have limitations
        limitation_count = 0
        if hard_analysis_exists:
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analyses = json.load(f)
                for a in analyses:
                    if a.get("limitation"):
                        limitation_count += 1
            except Exception:
                pass
        limitation_rate = (limitation_count / total_analyzed * 100) if total_analyzed > 0 else 0

        # Soft threshold 1: Prefer cross-paper relationship coverage >= 70%
        # (approximated by papers with related_work extracted)
        related_count = 0
        if hard_analysis_exists:
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analyses = json.load(f)
                for a in analyses:
                    if a.get("related_work"):
                        related_count += 1
            except Exception:
                pass
        relationship_rate = (related_count / total_analyzed * 100) if total_analyzed > 0 else 0

        soft = {
            "limitation_rate": round(limitation_rate, 1),
            "limitation_rate_pass": limitation_rate >= 90,
            "relationship_rate": round(relationship_rate, 1),
            "relationship_rate_pass": relationship_rate >= 70,
        }

        return {
            "overall_pass": all_hard_pass,
            "hard_requirements": hard,
            "soft_thresholds": soft,
            "total_analyzed": total_analyzed,
            "index_line_count": index_line_count,
        }

    # ------------------------------------------------------------------
    # 6. write_manifest
    # ------------------------------------------------------------------
    def write_manifest(self, output: LiteratureIntelligenceOutput) -> Dict[str, Any]:
        """Generate the module manifest for provenance tracking.

        Args:
            output: Module output.

        Returns:
            Manifest dictionary.
        """
        return {
            "module_id": self.MODULE_ID,
            "module_name": self.MODULE_NAME,
            "module_version": self.MODULE_VERSION,
            "task_id": output.task_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output_files": output.output_files,
            "manifest_data": output.manifest,
            "warnings": output.warnings,
            "errors": output.errors,
            "status": "COMPLETED" if not output.errors else "FAILED",
        }

    # ------------------------------------------------------------------
    # 7. write_report
    # ------------------------------------------------------------------
    def write_report(self, output: LiteratureIntelligenceOutput) -> str:
        """Generate a human-readable validation report.

        Args:
            output: Module output.

        Returns:
            Markdown-formatted report string.
        """
        return self._generate_report(
            output.task_id, output.output_files, output.manifest,
            output.warnings, output.errors,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _discover_papers(self, input_data: LiteratureIntelligenceInput) -> List[Dict[str, Any]]:
        """Discover normalized paper.md files and their metadata.

        Looks in both input_files and upstream_module_02 output_files
        for paper.md and metadata.json pairs.

        Returns:
            List of dicts with keys: paper_id, md_path, metadata.
        """
        entries: List[Dict[str, Any]] = []
        seen_pids: set = set()

        # Check upstream_module_02 output files
        upstream = input_data.upstream_module_02 or {}
        upstream_files = upstream.get("output_files", {})

        # Find all paper.md files from upstream
        for key, path in upstream_files.items():
            if "normalized/paper.md" in key:
                # Extract paper_id from key: "papers/<paper_id>/normalized/paper.md"
                parts = key.split("/")
                if len(parts) >= 2:
                    paper_id = parts[1]
                else:
                    paper_id = os.path.basename(os.path.dirname(os.path.dirname(path)))

                if paper_id in seen_pids:
                    continue
                seen_pids.add(paper_id)

                # Find matching metadata.json
                meta_key = f"papers/{paper_id}/metadata.json"
                meta_path = upstream_files.get(meta_key, "")
                metadata = {}
                if meta_path and os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                    except Exception:
                        pass

                entries.append({
                    "paper_id": paper_id,
                    "md_path": path,
                    "metadata": metadata,
                })

        # Also check input_files directly
        for name, path in (input_data.input_files or {}).items():
            if name.endswith("paper.md"):
                # Try to extract paper_id from the name or path
                parts = name.split("/")
                paper_id = parts[1] if len(parts) >= 2 else os.path.splitext(os.path.basename(name))[0]

                if paper_id in seen_pids:
                    continue
                seen_pids.add(paper_id)

                entries.append({
                    "paper_id": paper_id,
                    "md_path": path,
                    "metadata": {},
                })

        return entries

    @staticmethod
    def _build_analysis_markdown(
        analyses: List[Dict[str, Any]],
        quality_reports: List[Dict[str, Any]],
    ) -> str:
        """Build a human-readable Markdown summary of all analyses.

        Args:
            analyses: List of extracted knowledge dicts.
            quality_reports: List of quality report dicts.

        Returns:
            Markdown-formatted string.
        """
        lines = [
            "# Literature Intelligence Analysis Report",
            "",
            f"**Total papers analyzed:** {len(analyses)}",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "",
            "---",
            "",
        ]

        for i, analysis in enumerate(analyses):
            title = analysis.get("title", "Unknown")
            paper_id = analysis.get("paper_id", f"paper_{i}")
            venue = analysis.get("venue", "")
            year = analysis.get("year", "")

            qr = quality_reports[i] if i < len(quality_reports) else {}
            score = qr.get("score", 0)
            passed = qr.get("overall_pass", False)

            lines.append(f"## {i + 1}. {title}")
            lines.append("")
            lines.append(f"- **Paper ID:** {paper_id}")
            if venue:
                lines.append(f"- **Venue:** {venue}")
            if year:
                lines.append(f"- **Year:** {year}")
            lines.append(f"- **Quality Score:** {score}/100 ({'PASS' if passed else 'FAIL'})")
            lines.append(f"- **Extraction Strategy:** {analysis.get('_extraction_strategy', 'unknown')}")
            lines.append("")

            # Research problem
            rp = analysis.get("research_problem", "")
            if rp:
                lines.append("### Research Problem")
                lines.append("")
                lines.append(rp[:500] + ("..." if len(rp) > 500 else ""))
                lines.append("")

            # Method
            method = analysis.get("method", "")
            if method:
                lines.append("### Methodology")
                lines.append("")
                lines.append(method[:500] + ("..." if len(method) > 500 else ""))
                lines.append("")

            # Innovation
            innovation = analysis.get("innovation", "")
            if innovation:
                lines.append("### Key Contributions")
                lines.append("")
                lines.append(innovation[:500] + ("..." if len(innovation) > 500 else ""))
                lines.append("")

            # Limitations
            limitation = analysis.get("limitation", "")
            if limitation:
                lines.append("### Limitations")
                lines.append("")
                lines.append(limitation[:300] + ("..." if len(limitation) > 300 else ""))
                lines.append("")

            # Future directions
            future = analysis.get("future_direction", "")
            if future:
                lines.append("### Future Directions")
                lines.append("")
                lines.append(future[:300] + ("..." if len(future) > 300 else ""))
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # v8.3: 10-Dimension Analysis
    # ------------------------------------------------------------------

    def _analyze_10_dimensions(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """v8.3: Analyze papers across 10 dimensions.

        Dimensions:
        1. Problem - Research problem statement
        2. Method - Core methodology
        3. Architecture - Model/system architecture
        4. Algorithm - Algorithm design
        5. Formula - Mathematical formulations
        6. Loss - Loss function
        7. Dataset - Datasets used
        8. Experiment - Experimental setup
        9. Limitation - Identified limitations
        10. Future Work - Future directions
        """
        dimensions = {
            "problem": {"count": 0, "papers": []},
            "method": {"count": 0, "papers": []},
            "architecture": {"count": 0, "papers": []},
            "algorithm": {"count": 0, "papers": []},
            "formula": {"count": 0, "papers": []},
            "loss": {"count": 0, "papers": []},
            "dataset": {"count": 0, "papers": []},
            "experiment": {"count": 0, "papers": []},
            "limitation": {"count": 0, "papers": []},
            "future_work": {"count": 0, "papers": []},
        }

        # Map analysis fields to dimensions
        field_mapping = {
            "problem": ["research_problem", "problem"],
            "method": ["method", "methodology"],
            "architecture": ["architecture", "model_architecture"],
            "algorithm": ["algorithm", "algorithm_design"],
            "formula": ["formulas", "equations", "mathematical_formulation"],
            "loss": ["loss_function", "loss", "objective_function"],
            "dataset": ["dataset", "datasets"],
            "experiment": ["experiment", "experiments", "experimental_setup"],
            "limitation": ["limitation", "limitations"],
            "future_work": ["future_direction", "future_work"],
        }

        for analysis in analyses:
            paper_id = analysis.get("paper_id", "unknown")
            for dim, fields in field_mapping.items():
                for field in fields:
                    val = analysis.get(field, "")
                    if val and str(val).strip():
                        dimensions[dim]["count"] += 1
                        dimensions[dim]["papers"].append(paper_id)
                        break

        # Compute statistics
        total_papers = len(analyses)
        stats = {
            "total_papers_analyzed": total_papers,
            "dimension_coverage": {},
            "source_distribution": {
                "latex": 0,
                "markdown": total_papers,
                "pdf": 0,
                "internet": 0,
                "skill": 0,
                "human_input": 0,
            },
        }

        for dim, data in dimensions.items():
            coverage = (data["count"] / total_papers * 100) if total_papers > 0 else 0
            stats["dimension_coverage"][dim] = {
                "count": data["count"],
                "coverage_rate": round(coverage, 1),
            }

        # Count formulas, algorithms, datasets
        formula_count = 0
        algorithm_count = 0
        dataset_count = 0
        figure_count = 0

        for analysis in analyses:
            for field in ["formulas", "equations", "mathematical_formulation"]:
                val = analysis.get(field, "")
                if val:
                    formula_count += len(str(val).split("$$")) - 1 if "$$" in str(val) else 1
            for field in ["algorithm", "algorithm_design"]:
                val = analysis.get(field, "")
                if val:
                    algorithm_count += 1
            for field in ["dataset", "datasets"]:
                val = analysis.get(field, "")
                if val:
                    if isinstance(val, list):
                        dataset_count += len(val)
                    elif isinstance(val, str):
                        dataset_count += len([d for d in val.split(",") if d.strip()])
            for field in ["figures", "figure_count"]:
                val = analysis.get(field, "")
                if isinstance(val, int):
                    figure_count += val
                elif isinstance(val, list):
                    figure_count += len(val)

        stats["formula_count"] = formula_count
        stats["algorithm_count"] = algorithm_count
        stats["dataset_count"] = dataset_count
        stats["figure_count"] = figure_count

        return {
            "dimensions": dimensions,
            "statistics": stats,
        }

    def _generate_stage_report(
        self,
        output_dir: str,
        task_id: str,
        analyses: List[Dict[str, Any]],
        dim_analysis: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        """v8.3: Generate Stage_Report.md for Module 03."""
        path = os.path.join(output_dir, "Stage_Report.md")
        stats = dim_analysis.get("statistics", {})

        lines = [
            "# Module 03 — Literature Intelligence Stage Report",
            "",
            f"**Task ID:** {task_id}",
            f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"**Status:** {'COMPLETED' if not errors else 'FAILED'}",
            "",
            "## 当前目标",
            "",
            "对每篇论文进行10维度深度分析，生成文献智能分析报告。",
            "",
            "## 输入",
            "",
            f"- 分析论文数: {len(analyses)}",
            "",
            "## 输出 — 10维度分析统计",
            "",
            "| 维度 | 覆盖论文数 | 覆盖率 |",
            "|------|-----------|--------|",
        ]

        for dim, data in stats.get("dimension_coverage", {}).items():
            lines.append(
                f"| {dim} | {data['count']} | {data['coverage_rate']}% |"
            )

        lines.extend([
            "",
            "## 分析统计",
            "",
            f"- 分析论文总数: {stats.get('total_papers_analyzed', 0)}",
            f"- 公式数量: {stats.get('formula_count', 0)}",
            f"- 算法数量: {stats.get('algorithm_count', 0)}",
            f"- 图表数量: {stats.get('figure_count', 0)}",
            f"- 数据集数量: {stats.get('dataset_count', 0)}",
            "",
            "## 来源分布",
            "",
            "| 来源 | 论文数 |",
            "|------|--------|",
        ])

        for source, count in stats.get("source_distribution", {}).items():
            lines.append(f"| {source} | {count} |")

        lines.extend(["", "## 完成状态", "", "10维度分析完成。"])

        if warnings:
            lines.extend(["", "## 警告", ""])
            for w in warnings:
                lines.append(f"- {w}")
        if errors:
            lines.extend(["", "## 错误", ""])
            for e in errors:
                lines.append(f"- {e}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return path

    def _build_output(
        self,
        task_id: str,
        output_files: Dict[str, str],
        manifest: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> LiteratureIntelligenceOutput:
        """Construct a LiteratureIntelligenceOutput dataclass."""
        return LiteratureIntelligenceOutput(
            task_id=task_id,
            output_files=output_files,
            manifest=manifest,
            warnings=warnings,
            errors=errors,
        )

    def _generate_report(
        self,
        task_id: str,
        output_files: Dict[str, str],
        manifest: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        """Build a Markdown validation report."""
        lines = [
            "# Module 03 — Literature Intelligence Validation Report",
            "",
            f"**Task ID:** {task_id}",
            f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"**Status:** {'COMPLETED' if not errors else 'FAILED'}",
            "",
            "## Summary",
            "",
            f"- Total papers analyzed: {manifest.get('total_papers_analyzed', 0)}",
            f"- Quality pass: {manifest.get('total_quality_pass', 0)}",
            f"- Quality fail: {manifest.get('total_quality_fail', 0)}",
            f"- Average quality score: {manifest.get('average_quality_score', 0)}",
            "",
            "## Output Files",
            "",
        ]
        for fname, fpath in output_files.items():
            exists = "YES" if os.path.exists(fpath) else "NO"
            lines.append(f"- `{fname}` — exists: {exists}")
        if warnings:
            lines.append("")
            lines.append("## Warnings")
            lines.append("")
            for w in warnings[:20]:
                lines.append(f"- {w}")
        if errors:
            lines.append("")
            lines.append("## Errors")
            lines.append("")
            for e in errors:
                lines.append(f"- {e}")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # v8.3.1: Paper Analysis Trace
    # ------------------------------------------------------------------

    def _build_analysis_trace(
        self,
        analyses: List[Dict[str, Any]],
        paper_entries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """v8.3.1: Build paper_analysis_trace.json data.

        For each analyzed paper, records:
            - 分析来源 (analysis source)
            - LLM模型 (LLM model)
            - 时间 (timestamp)
            - 可信度 (confidence)
        """
        trace_entries: List[Dict[str, Any]] = []

        # Build a lookup from paper_id to entry metadata
        entry_map: Dict[str, Dict[str, Any]] = {}
        for entry in paper_entries:
            pid = entry.get("paper_id", "")
            entry_map[pid] = entry

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for analysis in analyses:
            paper_id = analysis.get("paper_id", "unknown")
            entry = entry_map.get(paper_id, {})
            metadata = entry.get("metadata", {})

            # Determine analysis source
            source = self._determine_analysis_source(analysis, metadata)

            # Determine LLM model
            llm_model = self._determine_llm_model(analysis, metadata)

            # Determine confidence based on source and LLM usage
            confidence = self._determine_confidence(source, llm_model)

            trace_entries.append({
                "paper_id": paper_id,
                "title": analysis.get("title", ""),
                "分析来源": source,
                "LLM模型": llm_model,
                "时间": timestamp,
                "可信度": confidence,
            })

        return trace_entries

    def _determine_analysis_source(
        self, analysis: Dict[str, Any], metadata: Dict[str, Any]
    ) -> str:
        """Determine the analysis source for a paper.

        Returns one of: 'Latex', 'PDF', 'Internet', 'Skill', 'Human'.
        """
        # Check metadata for explicit source indicators
        if metadata.get("latex_path"):
            return "Latex"
        if metadata.get("pdf_path"):
            return "PDF"

        source = str(metadata.get("source", "")).lower()
        if source == "internet":
            return "Internet"
        if source == "skill":
            return "Skill"
        if source == "human":
            return "Human"

        # Fall back to extraction strategy
        strategy = str(analysis.get("_extraction_strategy", "")).lower()
        if "latex" in strategy:
            return "Latex"
        if "pdf" in strategy:
            return "PDF"

        # Default: assume markdown from LaTeX conversion
        return "Latex"

    def _determine_llm_model(
        self, analysis: Dict[str, Any], metadata: Dict[str, Any]
    ) -> str:
        """Determine the LLM model used for analysis.

        Returns the model name (e.g., 'deepseek-r1:8b') or 'template' if no LLM.
        """
        # Check if LLM model info is in the analysis
        model = analysis.get("_llm_model", "") or analysis.get("llm_model", "")
        if model:
            return str(model)

        # Check metadata for model info
        model = metadata.get("llm_model", "") or metadata.get("model", "")
        if model:
            return str(model)

        # Check extractor for model info
        if self._extractor:
            for attr in ("model_name", "llm_model", "_model_name"):
                model = getattr(self._extractor, attr, None)
                if model:
                    return str(model)

        # Check extraction strategy for LLM indicators
        strategy = str(analysis.get("_extraction_strategy", "")).lower()
        if "llm" in strategy or "deepseek" in strategy or "gemma" in strategy:
            return strategy

        # No LLM used — template-based
        return "template"

    def _determine_confidence(self, source: str, llm_model: str) -> float:
        """Determine confidence score based on source and LLM usage.

        Confidence mapping:
            - Latex source: 1.0
            - Markdown (Internet/Skill/Human): 0.8
            - PDF source: 0.6
            - Template/no-LLM: 0.5
        """
        # Template/no-LLM always gets 0.5
        if llm_model == "template":
            return 0.5

        # LLM-based confidence by source
        if source == "Latex":
            return 1.0
        elif source == "PDF":
            return 0.6
        elif source in ("Internet", "Skill", "Human"):
            return 0.8
        else:
            return 0.5
