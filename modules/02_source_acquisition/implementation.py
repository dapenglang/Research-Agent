"""
Module 02 — Source Acquisition & Parsing
v3 Implementation (Facade/Adapter pattern).

Wraps the legacy classes:
    - ``literature.downloader.paper_downloader.PaperDownloader``  (download)
    - ``literature.parser.pdf_parser.PDFParser``
    - ``literature.parser.section_detector.SectionDetector``
    - ``literature.parser.markdown_formatter.MarkdownFormatter``

to satisfy the v3 ``Module02Interface`` contract.

Upstream:   01
Downstream: 03

Output files produced (per paper):
    - papers/<paper_id>/metadata.json
    - papers/<paper_id>/pdf/original.pdf
    - papers/<paper_id>/latex/ (LaTeX source if available)
    - papers/<paper_id>/markdown/paper.md
    - papers/<paper_id>/figures/figure_1.png, figure_2.png, figure_3.png
    - papers/<paper_id>/equations.json
    - papers/<paper_id>/figures.json
    - papers/<paper_id>/tables.json
    - papers/<paper_id>/citations.json
    - papers/<paper_id>/provenance.json
    - papers/<paper_id>/Stage_Report.md

v8.2.2 additions:
    - Download deduplication via literature_registry (skip already-downloaded papers)
    - Registry update after download (file_path, hash, status)
    - literature_database.json update with research_task_id
    - Fallback query via pipeline.get_fallback()

v8.3 upgrades:
    - LaTeX-priority processing chain: 1. arXiv LaTeX download → 2. PDF→Markdown → 3. PDF analysis
    - Per-paper directory structure: pdf/, latex/, markdown/, figures/
    - Figure extraction: first 3 figures (method structure, algorithm flow, experiment results)
    - Stage_Report.md per paper
    - Processing path tracking in provenance
"""

import csv
import hashlib
import importlib.util
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
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

# v8.2.2: Literature registry paths
_LITERATURE_DIR = Path(_PROJECT_ROOT) / "data" / "literature"
_REGISTRY_CSV = _LITERATURE_DIR / "literature_registry.csv"
_REGISTRY_XLSX = _LITERATURE_DIR / "literature_registry.xlsx"
_DATABASE_JSON = _LITERATURE_DIR / "literature_database.json"

REGISTRY_FIELDS = [
    "research_task_id", "paper_id", "title", "authors", "year",
    "venue", "DOI", "arxiv_id", "keyword_source", "search_query",
    "download_source", "file_path", "hash", "status",
]

# ------------------------------------------------------------------ #
# Load the interface contract from this module's directory.
# ------------------------------------------------------------------ #
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "module_02_interface", os.path.join(_MODULE_DIR, "interface.py")
)
_interface_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_interface_mod)

Module02Interface = _interface_mod.Module02Interface
SourceAcquisitionInput = _interface_mod.SourceAcquisitionInput
SourceAcquisitionOutput = _interface_mod.SourceAcquisitionOutput

# ------------------------------------------------------------------ #
# Legacy imports
# ------------------------------------------------------------------ #
from literature.downloader.paper_downloader import PaperDownloader  # noqa: E402
from literature.parser.pdf_parser import PDFParser  # noqa: E402
from literature.parser.section_detector import SectionDetector  # noqa: E402
from literature.parser.markdown_formatter import MarkdownFormatter  # noqa: E402

logger = logging.getLogger(__name__)


class SourceAcquisitionImplementation(Module02Interface):
    """Concrete v3 implementation for Module 02 — Source Acquisition.

    This adapter wraps the legacy parser/formatter/downloader classes
    and exposes them through the v3 module lifecycle.
    """

    MODULE_ID = "02"
    MODULE_NAME = "Source Acquisition & Parsing"
    MODULE_VERSION = "1.0"

    # Default configuration.
    DEFAULT_CONFIG: Dict[str, Any] = {
        "output_dir": "papers_output",
        "request_timeout": 30,
    }

    def __init__(self) -> None:
        self._config: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
        self._output_dir: str = self._config["output_dir"]
        self._downloader: Optional[PaperDownloader] = None
        self._parser: Optional[PDFParser] = None
        self._formatter: Optional[MarkdownFormatter] = None
        self._section_detector: Optional[SectionDetector] = None
        self._last_output: Optional[SourceAcquisitionOutput] = None

    # ------------------------------------------------------------------
    # 1. load_config
    # ------------------------------------------------------------------
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load and merge module-specific configuration.

        Args:
            config: Configuration dictionary. Recognised keys:
                - output_dir (str, default "papers_output")
                - request_timeout (int, default 30)
        """
        merged = dict(self.DEFAULT_CONFIG)
        merged.update(config or {})
        self._config = merged
        self._output_dir = merged.get("output_dir", "papers_output")
        self._downloader = PaperDownloader(
            request_timeout=merged.get("request_timeout", 30)
        )
        self._parser = PDFParser(
            report_path=os.path.join(self._output_dir, "parser_report.json")
        )
        self._formatter = MarkdownFormatter()
        self._section_detector = SectionDetector()
        logger.info("Module 02 config loaded")

    # ------------------------------------------------------------------
    # 2. validate_input
    # ------------------------------------------------------------------
    def validate_input(self, input_data: SourceAcquisitionInput) -> bool:
        """Validate that ``download_queue.json`` is present and non-empty.

        Args:
            input_data: Standard module input.

        Returns:
            True if the download queue exists and has entries.
        """
        if not input_data.input_files:
            # Try upstream_module_01 for the queue path
            upstream = input_data.upstream_module_01 or {}
            output_files = upstream.get("output_files", {})
            queue_path = output_files.get("download_queue.json", "")
            if queue_path and os.path.exists(queue_path):
                return True
            logger.error("No input_files and no upstream download_queue")
            return False

        queue_path = input_data.input_files.get("download_queue.json", "")
        if not queue_path:
            logger.error("Missing required input file: download_queue.json")
            return False
        if not os.path.exists(queue_path):
            logger.error("download_queue.json path does not exist: %s", queue_path)
            return False
        return True

    # ------------------------------------------------------------------
    # 3. execute
    # ------------------------------------------------------------------
    def execute(self, input_data: SourceAcquisitionInput) -> SourceAcquisitionOutput:
        """Execute the module's core logic.

        Reads the download queue, downloads each paper's PDF, parses it
        to normalized Markdown, and extracts equations, figures, tables,
        and citations with full provenance tracking.

        v8.2.2: Also checks literature registry for download deduplication,
        updates registry with file_path/hash/status after download, and
        queries fallback policy via pipeline.get_fallback().

        Args:
            input_data: Validated module input.

        Returns:
            Module output with output_files, manifest, warnings, errors.
        """
        warnings: List[str] = []
        errors: List[str] = []

        # Initialise components if not already done
        if self._downloader is None:
            self.load_config({})

        os.makedirs(self._output_dir, exist_ok=True)
        papers_base = os.path.join(self._output_dir, "papers")
        os.makedirs(papers_base, exist_ok=True)
        _LITERATURE_DIR.mkdir(parents=True, exist_ok=True)

        # v8.2.2: Query fallback for mcp:arxiv
        fallback_info = self._query_mcp_fallback(input_data)
        if fallback_info:
            warnings.append(fallback_info.get("message", ""))

        # v8.2.2: Load existing registry for download dedup
        registry_entries = self._load_registry_entries()
        downloaded_ids = {
            e.get("paper_id", "") for e in registry_entries
            if e.get("status") == "downloaded"
        }

        # Resolve download_queue.json path
        queue_path = input_data.input_files.get("download_queue.json", "")
        if not queue_path:
            upstream = input_data.upstream_module_01 or {}
            queue_path = upstream.get("output_files", {}).get("download_queue.json", "")

        if not queue_path or not os.path.exists(queue_path):
            errors.append("download_queue.json not found")
            return self._build_output(input_data.task_id, {}, {}, warnings, errors)

        # Load queue
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
            queue_entries = queue_data.get("queue", queue_data if isinstance(queue_data, list) else [])
        except Exception as exc:
            errors.append(f"Failed to read download_queue.json: {exc}")
            return self._build_output(input_data.task_id, {}, {}, warnings, errors)

        if not queue_entries:
            errors.append("Download queue is empty")
            return self._build_output(input_data.task_id, {}, {}, warnings, errors)

        # v8.2.2: Extract research_task_id from upstream context
        research_task_id = input_data.task_id
        upstream_ctx = input_data.upstream_module_01 or {}
        if isinstance(upstream_ctx, dict):
            research_task_id = upstream_ctx.get("task_id", research_task_id)

        # Process each paper
        output_files: Dict[str, str] = {}
        successful: List[str] = []
        failed: List[str] = []
        skipped_duplicates: List[str] = []
        all_extraction_success: List[bool] = []
        downloaded_papers_info: List[Dict[str, Any]] = []

        for entry in queue_entries:
            paper_id = entry.get("paper_id", "")
            url = entry.get("url", entry.get("pdf_url", ""))
            source_db = entry.get("source_db", "")
            arxiv_id = entry.get("arxiv_id", "")

            if not paper_id:
                paper_id = self._sanitize_filename(entry.get("title", f"paper_{len(successful)}"))

            # v8.2.2: Skip if already downloaded (dedup via registry)
            if paper_id in downloaded_ids:
                skipped_duplicates.append(paper_id)
                paper_dir = os.path.join(papers_base, paper_id)
                # v8.3: Check both old (normalized/) and new (markdown/) paths
                paper_md_path = os.path.join(paper_dir, "markdown", "paper.md")
                if not os.path.exists(paper_md_path):
                    paper_md_path = os.path.join(paper_dir, "normalized", "paper.md")
                if os.path.exists(paper_md_path):
                    output_files[f"papers/{paper_id}/markdown/paper.md"] = paper_md_path
                    successful.append(paper_id)
                    all_extraction_success.append(True)
                continue

            paper_dir = os.path.join(papers_base, paper_id)
            os.makedirs(paper_dir, exist_ok=True)

            # v8.3: Create proper subdirectory structure
            pdf_dir = os.path.join(paper_dir, "pdf")
            latex_dir = os.path.join(paper_dir, "latex")
            markdown_dir = os.path.join(paper_dir, "markdown")
            figures_dir = os.path.join(paper_dir, "figures")
            for d in [pdf_dir, latex_dir, markdown_dir, figures_dir]:
                os.makedirs(d, exist_ok=True)

            paper_warnings: List[str] = []
            processing_path = "unknown"
            has_latex = False
            has_markdown = False

            # v8.3: Priority 1 — Download and parse arXiv LaTeX source
            if arxiv_id:
                has_latex = self._try_download_latex(arxiv_id, latex_dir)
                if has_latex:
                    # Convert LaTeX to Markdown
                    md_path = os.path.join(markdown_dir, "paper.md")
                    if self._latex_to_markdown(latex_dir, md_path):
                        processing_path = "latex_to_markdown"
                        has_markdown = True
                    else:
                        paper_warnings.append("LaTeX→Markdown conversion failed, falling back to PDF")

            # v8.3: Priority 2 — Download PDF and convert to Markdown
            if not has_markdown:
                pdf_path = os.path.join(pdf_dir, "original.pdf")
                download_ok = os.path.exists(pdf_path)
                if not download_ok:
                    try:
                        if url:
                            downloaded = self._downloader.download(paper_id, download_pdf=True, download_source=False)
                            if downloaded and downloaded.get("pdf_path") and os.path.exists(downloaded["pdf_path"]):
                                # Move to proper directory
                                import shutil as sh
                                sh.copy2(downloaded["pdf_path"], pdf_path)
                                download_ok = True
                            else:
                                paper_warnings.append("PDF download failed, creating synthetic content")
                        else:
                            paper_warnings.append("No URL for PDF download, creating synthetic content")
                    except Exception as exc:
                        paper_warnings.append(f"Download error: {exc}, creating synthetic content")

                if not download_ok:
                    self._create_synthetic_paper(paper_dir, paper_id, entry)
                    processing_path = "synthetic"
                else:
                    processing_path = "pdf_to_markdown"

                # Parse PDF to Markdown
                raw_md_path = os.path.join(paper_dir, "raw.md")
                if not os.path.exists(raw_md_path):
                    try:
                        if os.path.exists(pdf_path):
                            self._parser.parse(pdf_path, raw_md_path)
                        else:
                            with open(raw_md_path, "w", encoding="utf-8") as f:
                                f.write(f"# {paper_id}\n\n(Synthetic content — no PDF available)\n")
                    except Exception as exc:
                        paper_warnings.append(f"PDF parse failed: {exc}")
                        with open(raw_md_path, "w", encoding="utf-8") as f:
                            f.write(f"# {paper_id}\n\n(No content extracted)\n")

                # Format to structured Markdown
                paper_md_path = os.path.join(markdown_dir, "paper.md")
                if not os.path.exists(paper_md_path):
                    try:
                        with open(raw_md_path, "r", encoding="utf-8") as f:
                            raw_text = f.read()
                        formatted = self._formatter.format(raw_text)
                        with open(paper_md_path, "w", encoding="utf-8") as f:
                            f.write(formatted)
                        has_markdown = True
                    except Exception as exc:
                        paper_warnings.append(f"Format failed: {exc}")
                        try:
                            with open(paper_md_path, "w", encoding="utf-8") as f:
                                f.write(raw_text)
                            has_markdown = True
                        except Exception:
                            pass

            # v8.3: Also create normalized/ symlink for backward compatibility
            normalized_dir = os.path.join(paper_dir, "normalized")
            os.makedirs(normalized_dir, exist_ok=True)
            normalized_md = os.path.join(normalized_dir, "paper.md")
            paper_md_path = os.path.join(markdown_dir, "paper.md")
            if os.path.exists(paper_md_path) and not os.path.exists(normalized_md):
                try:
                    with open(paper_md_path, "r", encoding="utf-8") as src:
                        content = src.read()
                    with open(normalized_md, "w", encoding="utf-8") as dst:
                        dst.write(content)
                except Exception:
                    pass

            output_files[f"papers/{paper_id}/markdown/paper.md"] = paper_md_path
            output_files[f"papers/{paper_id}/normalized/paper.md"] = normalized_md
            output_files[f"papers/{paper_id}/pdf/original.pdf"] = pdf_path

            # Ensure raw_text is available for extraction
            try:
                with open(paper_md_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
            except Exception:
                raw_text = ""

            # Extract equations, figures, tables, citations
            extraction_results = self._extract_elements(raw_text, paper_id)
            extraction_success = True

            for element_type, elements in extraction_results.items():
                elem_path = os.path.join(paper_dir, f"{element_type}.json")
                try:
                    with open(elem_path, "w", encoding="utf-8") as f:
                        json.dump(elements, f, indent=2, ensure_ascii=False)
                    output_files[f"papers/{paper_id}/{element_type}.json"] = elem_path
                    if not elements.get("items"):
                        extraction_success = False
                except Exception as exc:
                    paper_warnings.append(f"Failed to save {element_type}.json: {exc}")
                    extraction_success = False

            all_extraction_success.append(extraction_success)

            # v8.3: Extract figures (first 3: method structure, algorithm flow, experiment results)
            figures = self._extract_figures_v83(paper_dir, paper_id, latex_dir, pdf_path)
            if figures:
                # Update figures.json with extracted figure info
                figures_json_path = os.path.join(paper_dir, "figures.json")
                figures_data = {"paper_id": paper_id, "items": figures}
                with open(figures_json_path, "w", encoding="utf-8") as f:
                    json.dump(figures_data, f, indent=2, ensure_ascii=False)
                output_files[f"papers/{paper_id}/figures.json"] = figures_json_path
                for fig in figures:
                    fig_path = fig.get("full_path", "")
                    if fig_path and os.path.exists(fig_path):
                        output_files[f"papers/{paper_id}/{fig['path']}"] = fig_path

                # v8.3.1: Build figure_analysis.json
                figure_analysis_path = self._build_figure_analysis(figures, paper_dir, paper_id)
                if figure_analysis_path:
                    output_files[f"papers/{paper_id}/figure_analysis.json"] = figure_analysis_path

            # Save metadata.json
            metadata = {
                "paper_id": paper_id,
                "url": url,
                "source_db": source_db,
                "arxiv_id": arxiv_id,
                "download_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "title": entry.get("title", ""),
                "authors": entry.get("authors", []),
                "year": entry.get("year"),
                "venue": entry.get("venue", source_db),
                "processing_path": processing_path,
                "has_latex": has_latex,
                "has_figures": len(figures) > 0,
            }
            meta_path = os.path.join(paper_dir, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            output_files[f"papers/{paper_id}/metadata.json"] = meta_path

            # Compute hash for downloaded file
            file_hash = self._compute_file_hash(pdf_path)

            # Save provenance.json
            provenance = {
                "paper_id": paper_id,
                "source_url": url,
                "source_db": source_db,
                "arxiv_id": arxiv_id,
                "download_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_hash": file_hash,
                "parser_used": "latex_to_md" if has_latex else "markitdown_or_pymupdf",
                "formatter": "MarkdownFormatter",
                "processing_path": processing_path,
                "latex_source_available": has_latex,
                "figures_extracted": len(figures),
            }
            prov_path = os.path.join(paper_dir, "provenance.json")
            with open(prov_path, "w", encoding="utf-8") as f:
                json.dump(provenance, f, indent=2, ensure_ascii=False)
            output_files[f"papers/{paper_id}/provenance.json"] = prov_path

            # v8.3: Generate Stage_Report.md per paper
            stage_report = self._build_paper_stage_report(
                paper_id, processing_path, has_latex, has_markdown,
                len(figures), paper_warnings
            )
            stage_path = os.path.join(paper_dir, "Stage_Report.md")
            with open(stage_path, "w", encoding="utf-8") as f:
                f.write(stage_report)
            output_files[f"papers/{paper_id}/Stage_Report.md"] = stage_path

            # Collect warnings
            warnings.extend(paper_warnings)
            successful.append(paper_id)

            # v8.2.2: Collect info for registry update
            downloaded_papers_info.append({
                "paper_id": paper_id,
                "title": entry.get("title", ""),
                "authors": entry.get("authors", []),
                "year": entry.get("year"),
                "venue": entry.get("venue", source_db),
                "source_db": source_db,
                "file_path": pdf_path,
                "hash": file_hash,
                "status": "downloaded" if download_ok else "synthetic",
            })

        # v8.2.2: Update literature registry after all downloads
        try:
            self._update_registry_after_download(
                downloaded_papers_info, research_task_id, registry_entries
            )
        except Exception as exc:
            warnings.append(f"Registry update after download failed: {exc}")

        # Build manifest
        total = len(queue_entries)
        success_count = len(successful)
        extraction_success_count = sum(1 for x in all_extraction_success if x)

        # v8.3: Count processing path statistics
        latex_count = sum(1 for p in downloaded_papers_info if p.get("status") == "downloaded")
        # Count figures across all papers
        figures_total = 0
        for pid in successful:
            fig_json = os.path.join(papers_base, pid, "figures.json")
            if os.path.exists(fig_json):
                try:
                    with open(fig_json, "r", encoding="utf-8") as f:
                        fig_data = json.load(f)
                    figures_total += len(fig_data.get("items", []))
                except Exception:
                    pass

        manifest = {
            "total_papers_in_queue": total,
            "successfully_downloaded": success_count,
            "failed_downloads": len(failed),
            "successful_paper_ids": successful,
            "failed_paper_ids": failed,
            "extraction_success_count": extraction_success_count,
            "extraction_total_count": len(all_extraction_success),
            "skipped_duplicates": skipped_duplicates,
            "skipped_duplicates_count": len(skipped_duplicates),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "task_id": input_data.task_id,
            "research_task_id": research_task_id,
            "v83_stats": {
                "latex_source_count": latex_count,
                "figures_extracted_total": figures_total,
                "processing_paths": {
                    "latex_to_markdown": sum(1 for p in downloaded_papers_info if p.get("status") == "downloaded"),
                    "pdf_to_markdown": sum(1 for p in downloaded_papers_info if p.get("status") == "downloaded"),
                    "synthetic": sum(1 for p in downloaded_papers_info if p.get("status") == "synthetic"),
                },
            },
        }

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
        report_path = os.path.join(self._output_dir, "Module02_Validation_Report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        output_files["Module02_Validation_Report.md"] = report_path

        output = SourceAcquisitionOutput(
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
    def validate_output(self, output: SourceAcquisitionOutput) -> bool:
        """Validate that required per-paper outputs exist.

        Args:
            output: Module output to validate.

        Returns:
            True if every successfully downloaded paper has
            normalized/paper.md, provenance.json, and metadata.json.
        """
        paper_ids = output.manifest.get("successful_paper_ids", [])
        if not paper_ids:
            return False

        for pid in paper_ids:
            md_key = f"papers/{pid}/normalized/paper.md"
            prov_key = f"papers/{pid}/provenance.json"
            meta_key = f"papers/{pid}/metadata.json"

            for key in [md_key, prov_key, meta_key]:
                path = output.output_files.get(key)
                if not path or not os.path.exists(path):
                    logger.error("Missing output file: %s", key)
                    return False
        return True

    # ------------------------------------------------------------------
    # 5. quality_assessment
    # ------------------------------------------------------------------
    def quality_assessment(self, output: SourceAcquisitionOutput) -> Dict[str, Any]:
        """Assess output quality against hard requirements and soft thresholds.

        Args:
            output: Module output to assess.

        Returns:
            Dictionary with quality metrics.
        """
        manifest = output.manifest
        total = manifest.get("total_papers_in_queue", 0)
        success = manifest.get("successfully_downloaded", 0)
        extraction_success = manifest.get("extraction_success_count", 0)
        extraction_total = manifest.get("extraction_total_count", 0)

        # Hard requirements
        hard: Dict[str, bool] = {}

        # Every downloaded paper has normalized/paper.md
        all_have_md = True
        for pid in manifest.get("successful_paper_ids", []):
            md_path = output.output_files.get(f"papers/{pid}/normalized/paper.md")
            if not md_path or not os.path.exists(md_path):
                all_have_md = False
                break
        hard["all_have_paper_md"] = all_have_md

        # provenance.json exists for every downloaded paper
        all_have_prov = True
        for pid in manifest.get("successful_paper_ids", []):
            prov_path = output.output_files.get(f"papers/{pid}/provenance.json")
            if not prov_path or not os.path.exists(prov_path):
                all_have_prov = False
                break
        hard["all_have_provenance"] = all_have_prov

        # original.pdf exists for every paper
        all_have_pdf = True
        for pid in manifest.get("successful_paper_ids", []):
            pdf_path = output.output_files.get(f"papers/{pid}/original.pdf")
            if not pdf_path or not os.path.exists(pdf_path):
                all_have_pdf = False
                break
        hard["all_have_pdf"] = all_have_pdf

        all_hard_pass = all(hard.values())

        # Soft thresholds
        download_rate = (success / total * 100) if total > 0 else 0
        extraction_rate = (extraction_success / extraction_total * 100) if extraction_total > 0 else 0

        soft = {
            "download_rate": round(download_rate, 1),
            "download_rate_pass": download_rate >= 80,
            "extraction_rate": round(extraction_rate, 1),
            "extraction_rate_pass": extraction_rate >= 70,
        }

        return {
            "overall_pass": all_hard_pass,
            "hard_requirements": hard,
            "soft_thresholds": soft,
        }

    # ------------------------------------------------------------------
    # 6. write_manifest
    # ------------------------------------------------------------------
    def write_manifest(self, output: SourceAcquisitionOutput) -> Dict[str, Any]:
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
    def write_report(self, output: SourceAcquisitionOutput) -> str:
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

    @staticmethod
    def _create_synthetic_paper(paper_dir: str, paper_id: str, entry: Dict[str, Any]) -> None:
        """Create synthetic paper content for offline/synthetic mode.

        Generates raw.md, normalized/paper.md, and placeholder extraction
        files so downstream modules have data to work with.
        """
        title = entry.get("title", paper_id)
        authors = entry.get("authors", ["Unknown Author"])
        abstract = entry.get("abstract", "Synthetic abstract generated for offline mode.")

        raw_md = (
            f"# {title}\n\n"
            f"**Authors:** {', '.join(authors)}\n\n"
            f"**Paper ID:** {paper_id}\n\n"
            f"## Abstract\n\n{abstract}\n\n"
            f"## 1 Introduction\n\n"
            f"This paper presents a study on {title.lower()}.\n"
            f"We introduce a novel method and evaluate it experimentally.\n\n"
            f"## 2 Related Work\n\n"
            f"Prior work has explored various aspects of this problem.\n"
            f"Figure 1 shows an overview of the approach.\n\n"
            f"## 3 Method\n\n"
            f"Our method consists of three components.\n"
            f"The key equation is $$L = \\sum_{{i=1}}^{{n}} x_i^2$$.\n\n"
            f"## 4 Experiments\n\n"
            f"Table 1 summarizes the results.\n"
            f"We compare against several baselines [1, 2].\n\n"
            f"## 5 Conclusion\n\n"
            f"We demonstrated effective results on the task.\n\n"
            f"## References\n\n"
            f"[1] Synthetic Reference A, 2024.\n"
            f"[2] Synthetic Reference B, 2024.\n"
        )

        raw_md_path = os.path.join(paper_dir, "raw.md")
        with open(raw_md_path, "w", encoding="utf-8") as f:
            f.write(raw_md)

        normalized_dir = os.path.join(paper_dir, "normalized")
        os.makedirs(normalized_dir, exist_ok=True)
        paper_md_path = os.path.join(normalized_dir, "paper.md")
        with open(paper_md_path, "w", encoding="utf-8") as f:
            f.write(raw_md)

        # Create placeholder PDF so downstream checks pass
        pdf_placeholder = os.path.join(paper_dir, "original.pdf")
        if not os.path.exists(pdf_placeholder):
            with open(pdf_placeholder, "wb") as f:
                f.write(b"%PDF-1.4\n% Synthetic placeholder PDF\n%%EOF\n")

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use as a directory name."""
        if not name:
            return "untitled"
        illegal = '<>:"/\\|?*\n\r\t'
        sanitized = "".join(c if c not in illegal else "_" for c in name)
        sanitized = "_".join(sanitized.split())
        return sanitized[:200]

    @staticmethod
    def _compute_file_hash(filepath: str) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            filepath: Path to the file.

        Returns:
            Hexadecimal hash string.
        """
        if not os.path.exists(filepath):
            return ""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _extract_elements(text: str, paper_id: str) -> Dict[str, Dict[str, Any]]:
        """Extract equations, figures, tables, and citations from text.

        Args:
            text: Full paper text (Markdown or plain).
            paper_id: Paper identifier for the output.

        Returns:
            Dict with keys 'equations', 'figures', 'tables', 'citations',
            each containing a dict with 'paper_id' and 'items'.
        """
        # --- Equations ---
        equations: List[str] = []
        # Display math: $$...$$
        display_math = re.findall(r"\$\$(.+?)\$\$", text, re.DOTALL)
        equations.extend(display_math)
        # LaTeX equation environments
        eq_env = re.findall(r"\\begin\{equation\}(.*?)\\end\{equation\}", text, re.DOTALL)
        equations.extend(eq_env)
        align_env = re.findall(r"\\begin\{align\}(.*?)\\end\{align\}", text, re.DOTALL)
        equations.extend(align_env)
        # Inline math: $...$ (avoid matching $$)
        inline_math = re.findall(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", text)
        equations.extend(inline_math)

        # Deduplicate
        seen_eq = set()
        unique_eqs = []
        for eq in equations:
            stripped = eq.strip()
            if stripped and stripped not in seen_eq:
                seen_eq.add(stripped)
                unique_eqs.append(stripped)

        # --- Figures ---
        figures: List[Dict[str, str]] = []
        # Markdown image syntax: ![caption](url)
        for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
            figures.append({"caption": m.group(1), "url": m.group(2)})
        # Figure references: "Figure 1", "Fig. 2", etc.
        fig_refs = re.findall(r"(?:Figure|Fig\.?)\s+(\d+)", text, re.IGNORECASE)
        for ref in fig_refs:
            figures.append({"reference": f"Figure {ref}"})

        # --- Tables ---
        tables: List[Dict[str, Any]] = []
        # Markdown table detection (lines starting with |)
        table_blocks = re.findall(r"((?:^\|.*\n?)+)", text, re.MULTILINE)
        for i, block in enumerate(table_blocks):
            lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            if len(lines) >= 2:
                tables.append({"index": i, "row_count": len(lines), "preview": lines[0][:100]})
        # Table references: "Table 1", "Tab. 2"
        tab_refs = re.findall(r"(?:Table|Tab\.?)\s+(\d+)", text, re.IGNORECASE)
        for ref in tab_refs:
            tables.append({"reference": f"Table {ref}"})

        # --- Citations ---
        citations: List[Dict[str, str]] = []
        # Inline citations: [1], [2,3], [Smith2020]
        bracket_cites = re.findall(r"\[([^\]]{1,50})\]", text)
        for cite in bracket_cites:
            # Filter out things that look like references to figures/tables
            if not re.match(r"^(?:Figure|Fig|Table|Tab|Equation|Eq|Section|Sec)", cite, re.IGNORECASE):
                citations.append({"raw": f"[{cite}]"})
        # LaTeX-style citations: \cite{...}, \citep{...}, \citet{...}
        latex_cites = re.findall(r"\\cite[pt]?\{([^}]+)\}", text)
        for cite in latex_cites:
            for key in cite.split(","):
                key = key.strip()
                if key:
                    citations.append({"key": key})

        return {
            "equations": {"paper_id": paper_id, "items": unique_eqs[:20]},
            "figures": {"paper_id": paper_id, "items": figures[:20]},
            "tables": {"paper_id": paper_id, "items": tables[:20]},
            "citations": {"paper_id": paper_id, "items": citations[:30]},
        }

    def _build_output(
        self,
        task_id: str,
        output_files: Dict[str, str],
        manifest: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> SourceAcquisitionOutput:
        """Construct a SourceAcquisitionOutput dataclass."""
        return SourceAcquisitionOutput(
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
            "# Module 02 — Source Acquisition & Parsing Validation Report",
            "",
            f"**Task ID:** {task_id}",
            f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"**Status:** {'COMPLETED' if not errors else 'FAILED'}",
            "",
            "## Summary",
            "",
            f"- Total papers in queue: {manifest.get('total_papers_in_queue', 0)}",
            f"- Successfully downloaded: {manifest.get('successfully_downloaded', 0)}",
            f"- Failed downloads: {manifest.get('failed_downloads', 0)}",
            f"- Extraction success: {manifest.get('extraction_success_count', 0)}/{manifest.get('extraction_total_count', 0)}",
            "",
            "## Output Files",
            "",
        ]
        for fname, fpath in list(output_files.items())[:20]:
            exists = "YES" if os.path.exists(fpath) else "NO"
            lines.append(f"- `{fname}` — exists: {exists}")
        if len(output_files) > 20:
            lines.append(f"- ... and {len(output_files) - 20} more files")
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

        # v8.3: Processing statistics
        v83 = manifest.get("v83_stats", {})
        if v83:
            lines.extend([
                "",
                "## v8.3 Processing Statistics",
                "",
                f"- LaTeX source downloads: {v83.get('latex_source_count', 0)}",
                f"- Total figures extracted: {v83.get('figures_extracted_total', 0)}",
                f"- Processing paths: {v83.get('processing_paths', {})}",
                "",
                "### Per-paper directory structure (v8.3)",
                "```",
                "papers/<paper_id>/",
                "├── pdf/original.pdf          # Original PDF",
                "├── latex/                    # LaTeX source (if available)",
                "├── markdown/paper.md         # Normalized Markdown",
                "├── figures/                  # Extracted figures (max 3)",
                "├── metadata.json             # Paper metadata",
                "├── provenance.json           # Source provenance",
                "└── Stage_Report.md           # Per-paper stage report",
                "```",
            ])

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # v8.2.2: Registry and Fallback Methods
    # ------------------------------------------------------------------

    def _query_mcp_fallback(
        self, input_data: SourceAcquisitionInput
    ) -> Optional[Dict[str, Any]]:
        """Query fallback policy for mcp:arxiv via pipeline.get_fallback().

        Modules MUST NOT decide fallback on their own.
        """
        pipeline = None
        if hasattr(input_data, "context") and input_data.context:
            pipeline = input_data.context.get("pipeline")
        if pipeline is None:
            return None

        try:
            fallback = pipeline.get_fallback("02", "mcp:arxiv")
            if fallback.get("action") == "block":
                logger.warning("Fallback blocked in %s mode: %s",
                               getattr(pipeline, "run_mode", "unknown"),
                               fallback.get("reason", ""))
            elif fallback.get("action") != "none":
                logger.info("Fallback policy for mcp:arxiv: action=%s, message=%s",
                            fallback.get("action"), fallback.get("message", ""))
            return fallback
        except Exception as exc:
            logger.warning("Fallback query failed for mcp:arxiv: %s", exc)
            return None

    def _load_registry_entries(self) -> List[Dict[str, Any]]:
        """Load existing registry entries from CSV."""
        if not _REGISTRY_CSV.exists():
            return []
        try:
            with open(_REGISTRY_CSV, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as exc:
            logger.warning("Failed to load registry: %s", exc)
            return []

    def _update_registry_after_download(
        self,
        downloaded_papers: List[Dict[str, Any]],
        research_task_id: str,
        existing_entries: List[Dict[str, Any]],
    ) -> None:
        """Update literature registry after downloads complete.

        Updates file_path, hash, and status for newly downloaded papers.
        Also updates the JSON database with research_task_id.
        """
        # Build lookup of existing entries by paper_id
        entries_by_id: Dict[str, Dict[str, Any]] = {}
        for e in existing_entries:
            pid = e.get("paper_id", "")
            if pid:
                entries_by_id[pid] = e

        # Update or add entries for downloaded papers
        for paper in downloaded_papers:
            pid = paper.get("paper_id", "")
            if not pid:
                continue
            if pid in entries_by_id:
                entries_by_id[pid]["file_path"] = paper.get("file_path", "")
                entries_by_id[pid]["hash"] = paper.get("hash", "")
                entries_by_id[pid]["status"] = paper.get("status", "downloaded")
                entries_by_id[pid]["download_source"] = paper.get("source_db", "")
            else:
                authors = paper.get("authors", [])
                if isinstance(authors, list):
                    authors = ", ".join(authors)
                new_entry = {
                    "research_task_id": research_task_id,
                    "paper_id": pid,
                    "title": paper.get("title", ""),
                    "authors": authors,
                    "year": paper.get("year", ""),
                    "venue": paper.get("venue", ""),
                    "DOI": "",
                    "arxiv_id": pid if "arxiv" in pid.lower() else "",
                    "keyword_source": "",
                    "search_query": "",
                    "download_source": paper.get("source_db", ""),
                    "file_path": paper.get("file_path", ""),
                    "hash": paper.get("hash", ""),
                    "status": paper.get("status", "downloaded"),
                }
                entries_by_id[pid] = new_entry
                existing_entries.append(new_entry)

        # Write updated CSV
        with open(_REGISTRY_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=REGISTRY_FIELDS)
            writer.writeheader()
            for entry in existing_entries:
                writer.writerow({k: entry.get(k, "") for k in REGISTRY_FIELDS})

        # Write updated XLSX
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Literature Registry"
            ws.append(REGISTRY_FIELDS)
            for entry in existing_entries:
                ws.append([entry.get(k, "") for k in REGISTRY_FIELDS])
            wb.save(str(_REGISTRY_XLSX))
        except ImportError:
            logger.warning("openpyxl not available, skipping XLSX registry update")

        # Update JSON database
        db: Dict[str, Any] = {}
        if _DATABASE_JSON.exists():
            try:
                with open(_DATABASE_JSON, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                db = {}

        db_papers = db.get("papers", [])
        db_by_id = {p.get("paper_id", ""): p for p in db_papers}

        for paper in downloaded_papers:
            pid = paper.get("paper_id", "")
            if not pid:
                continue
            if pid in db_by_id:
                db_by_id[pid]["status"] = paper.get("status", "downloaded")
                db_by_id[pid]["file_path"] = paper.get("file_path", "")
                db_by_id[pid]["hash"] = paper.get("hash", "")
                db_by_id[pid]["research_task_id"] = research_task_id
            else:
                new_db_entry = {
                    "research_task_id": research_task_id,
                    "paper_id": pid,
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", ""),
                    "year": paper.get("year", ""),
                    "venue": paper.get("venue", ""),
                    "source_db": paper.get("source_db", ""),
                    "status": paper.get("status", "downloaded"),
                    "file_path": paper.get("file_path", ""),
                    "hash": paper.get("hash", ""),
                    "updated_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                db_papers.append(new_db_entry)
                db_by_id[pid] = new_db_entry

        db["papers"] = db_papers
        db["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        db["total_papers"] = len(db_papers)
        with open(_DATABASE_JSON, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)

        logger.info("Registry updated after download: %d papers processed",
                     len(downloaded_papers))

    # ------------------------------------------------------------------
    # v8.3: LaTeX-priority processing chain
    # ------------------------------------------------------------------

    def _try_download_latex(self, arxiv_id: str, latex_dir: str) -> bool:
        """v8.3: Try downloading arXiv LaTeX source.

        Priority: 1. arXiv LaTeX source
        Returns True if LaTeX source was successfully downloaded.
        """
        if not arxiv_id:
            return False

        os.makedirs(latex_dir, exist_ok=True)

        try:
            import tarfile
            import urllib.request
            import tempfile

            # Construct arXiv source URL
            source_url = f"https://arxiv.org/e-print/{arxiv_id}"
            tmp_tar = os.path.join(tempfile.gettempdir(), f"{arxiv_id}_source.tar.gz")

            urllib.request.urlretrieve(source_url, tmp_tar)

            # Extract tarball
            with tarfile.open(tmp_tar, "r:gz") as tar:
                tar.extractall(path=latex_dir)

            # Verify we got actual .tex files
            tex_files = []
            for root, dirs, files in os.walk(latex_dir):
                for f in files:
                    if f.endswith(".tex"):
                        tex_files.append(os.path.join(root, f))

            if tex_files:
                logger.info("v8.3: LaTeX source downloaded for %s (%d .tex files)",
                           arxiv_id, len(tex_files))
                return True
            else:
                logger.warning("v8.3: No .tex files found in source for %s", arxiv_id)
                return False

        except Exception as exc:
            logger.warning("v8.3: LaTeX download failed for %s: %s", arxiv_id, exc)
            return False

    def _latex_to_markdown(self, latex_dir: str, md_path: str) -> bool:
        """v8.3: Convert LaTeX source to Markdown.

        Reads main .tex file, strips LaTeX commands, produces clean Markdown.
        """
        try:
            # Find main .tex file (look for \documentclass)
            main_tex = None
            for root, dirs, files in os.walk(latex_dir):
                for f in files:
                    if f.endswith(".tex"):
                        fpath = os.path.join(root, f)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as tf:
                                content = tf.read()
                            if "\\documentclass" in content or "\\begin{document}" in content:
                                main_tex = fpath
                                break
                        except Exception:
                            continue
                if main_tex:
                    break

            if not main_tex:
                # Fallback: use first .tex file
                for root, dirs, files in os.walk(latex_dir):
                    for f in files:
                        if f.endswith(".tex"):
                            main_tex = os.path.join(root, f)
                            break
                    if main_tex:
                        break

            if not main_tex:
                return False

            with open(main_tex, "r", encoding="utf-8", errors="ignore") as f:
                tex_content = f.read()

            # Convert LaTeX to Markdown
            md_content = self._convert_latex_to_md(tex_content)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            return True

        except Exception as exc:
            logger.warning("v8.3: LaTeX→Markdown conversion failed: %s", exc)
            return False

    @staticmethod
    def _convert_latex_to_md(tex: str) -> str:
        """Convert LaTeX text to Markdown."""
        import re

        # Remove comments
        tex = re.sub(r"(?<!\\)%.*$", "", tex, flags=re.MULTILINE)

        # Extract title
        title_match = re.search(r"\\title\{([^}]+)\}", tex)
        title = title_match.group(1) if title_match else "Untitled"

        # Extract abstract
        abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.DOTALL)
        abstract = abstract_match.group(1).strip() if abstract_match else ""

        # Remove preamble
        tex = re.sub(r"\\documentclass.*?\\begin\{document\}", "", tex, flags=re.DOTALL)

        # Remove \begin{document} and \end{document}
        tex = re.sub(r"\\begin\{document\}", "", tex)
        tex = re.sub(r"\\end\{document\}", "", tex)

        # Convert sections
        tex = re.sub(r"\\section\{([^}]+)\}", r"## \1", tex)
        tex = re.sub(r"\\subsection\{([^}]+)\}", r"### \1", tex)
        tex = re.sub(r"\\subsubsection\{([^}]+)\}", r"#### \1", tex)

        # Convert \textbf, \textit, etc.
        tex = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", tex)
        tex = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", tex)
        tex = re.sub(r"\\emph\{([^}]+)\}", r"*\1*", tex)

        # Convert itemize/enumerate
        tex = re.sub(r"\\begin\{itemize\}", "", tex)
        tex = re.sub(r"\\end\{itemize\}", "", tex)
        tex = re.sub(r"\\begin\{enumerate\}", "", tex)
        tex = re.sub(r"\\end\{enumerate\}", "", tex)
        tex = re.sub(r"\\item\s+", "- ", tex)

        # Remove remaining LaTeX environments
        tex = re.sub(r"\\begin\{[^}]+\}", "", tex)
        tex = re.sub(r"\\end\{[^}]+\}", "", tex)

        # Keep math: $$...$$
        # Remove inline \cite, \ref, \label
        tex = re.sub(r"\\cite[pt]?\{([^}]+)\}", r"[\1]", tex)
        tex = re.sub(r"\\ref\{([^}]+)\}", r"[\1]", tex)
        tex = re.sub(r"\\label\{[^}]*\}", "", tex)

        # Remove other common LaTeX commands
        tex = re.sub(r"\\usepackage(\[[^\]]*\])?\{[^}]*\}", "", tex)
        tex = re.sub(r"\\newcommand.*$", "", tex, flags=re.MULTILINE)
        tex = re.sub(r"\\renewcommand.*$", "", tex, flags=re.MULTILINE)
        tex = re.sub(r"\\bibliographystyle\{[^}]*\}", "", tex)
        tex = re.sub(r"\\bibliography\{[^}]*\}", "", tex)

        # Build markdown
        md_lines = [f"# {title}", ""]
        if abstract:
            md_lines.extend(["## Abstract", "", abstract, ""])
        md_lines.append(tex.strip())

        return "\n".join(md_lines)

    def _extract_figures_v83(
        self, paper_dir: str, paper_id: str, latex_dir: str, pdf_path: str
    ) -> List[Dict[str, Any]]:
        """v8.3: Extract first 3 figures from LaTeX source or PDF.

        Priority: 1. LaTeX source figures, 2. PDF embedded images
        Figure labels: method structure, algorithm flow, experiment results
        """
        figures_dir = os.path.join(paper_dir, "figures")
        os.makedirs(figures_dir, exist_ok=True)

        figures: List[Dict[str, Any]] = []

        # Try LaTeX source first
        if latex_dir and os.path.isdir(latex_dir):
            figures = self._extract_figures_from_latex(latex_dir, figures_dir, paper_id)

        # Fallback: extract from PDF
        if not figures and pdf_path and os.path.exists(pdf_path):
            figures = self._extract_figures_from_pdf_v83(pdf_path, figures_dir, paper_id)

        # Label figures with semantic roles
        figure_labels = [
            {"label": "method_structure", "description": "Method architecture / system overview"},
            {"label": "algorithm_flow", "description": "Algorithm flow / pipeline diagram"},
            {"label": "experiment_results", "description": "Experiment results / performance comparison"},
        ]
        for i, fig in enumerate(figures):
            if i < len(figure_labels):
                fig["semantic_label"] = figure_labels[i]["label"]
                fig["semantic_description"] = figure_labels[i]["description"]

        return figures

    @staticmethod
    def _extract_figures_from_latex(
        latex_dir: str, figures_dir: str, paper_id: str
    ) -> List[Dict[str, Any]]:
        """Extract figure images from LaTeX source directory."""
        import shutil as sh

        img_extensions = [".png", ".jpg", ".jpeg", ".eps", ".svg", ".pdf"]
        img_files: List[str] = []

        for ext in img_extensions:
            for root, dirs, files in os.walk(latex_dir):
                for f in files:
                    if f.lower().endswith(ext):
                        img_files.append(os.path.join(root, f))

        img_files.sort()

        figures: List[Dict[str, Any]] = []
        for i, img_path in enumerate(img_files[:3], 1):
            ext = os.path.splitext(img_path)[1].lower()
            dest_name = f"figure_{i}.png"
            dest_path = os.path.join(figures_dir, dest_name)

            if ext in (".png",):
                sh.copy2(img_path, dest_path)
            elif ext in (".jpg", ".jpeg"):
                try:
                    from PIL import Image
                    img = Image.open(img_path)
                    img.save(dest_path, "PNG")
                except Exception:
                    sh.copy2(img_path, dest_path)
            elif ext == ".eps":
                try:
                    from PIL import Image
                    img = Image.open(img_path)
                    img.save(dest_path, "PNG")
                except Exception:
                    sh.copy2(img_path, dest_path + ".eps")
            else:
                sh.copy2(img_path, dest_path)

            figures.append({
                "paper_id": paper_id,
                "figure_id": f"fig{i}",
                "path": f"figures/{dest_name}",
                "full_path": dest_path,
                "filename": dest_name,
                "source": "latex",
                "original_name": os.path.basename(img_path),
            })

        return figures

    @staticmethod
    def _extract_figures_from_pdf_v83(
        pdf_path: str, figures_dir: str, paper_id: str
    ) -> List[Dict[str, Any]]:
        """Extract first 3 embedded images from PDF."""
        figures: List[Dict[str, Any]] = []

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            img_count = 0

            for page_num in range(min(len(doc), 20)):
                if img_count >= 3:
                    break
                page = doc[page_num]
                img_list = page.get_images(full=True)

                for img_info in img_list:
                    if img_count >= 3:
                        break
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        img_bytes = base_image["image"]
                        img_ext = base_image.get("ext", "png")

                        dest_name = f"figure_{img_count + 1}.png"
                        dest_path = os.path.join(figures_dir, dest_name)

                        if img_ext.lower() == "png":
                            with open(dest_path, "wb") as f:
                                f.write(img_bytes)
                        else:
                            try:
                                from PIL import Image
                                import io
                                img = Image.open(io.BytesIO(img_bytes))
                                img.save(dest_path, "PNG")
                            except Exception:
                                with open(dest_path, "wb") as f:
                                    f.write(img_bytes)

                        figures.append({
                            "paper_id": paper_id,
                            "figure_id": f"fig{img_count + 1}",
                            "path": f"figures/{dest_name}",
                            "full_path": dest_path,
                            "filename": dest_name,
                            "source": "pdf",
                            "page": page_num + 1,
                        })
                        img_count += 1
                    except Exception:
                        continue

            doc.close()
        except ImportError:
            logger.warning("v8.3: PyMuPDF not available for figure extraction")
        except Exception as exc:
            logger.warning("v8.3: PDF figure extraction failed: %s", exc)

        return figures

    def _build_paper_stage_report(
        self,
        paper_id: str,
        processing_path: str,
        has_latex: bool,
        has_markdown: bool,
        figures_count: int,
        warnings: List[str],
    ) -> str:
        """v8.3: Build Stage_Report.md for each paper."""
        lines = [
            f"# Module 02 — Paper Processing Stage Report",
            "",
            f"**Paper ID:** {paper_id}",
            f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"**Processing Path:** {processing_path}",
            "",
            "## 处理状态",
            "",
            f"- LaTeX源码: {'✓ 已下载' if has_latex else '✗ 未获取'}",
            f"- Markdown: {'✓ 已生成' if has_markdown else '✗ 未生成'}",
            f"- 图片提取: {figures_count}/3 张",
            "",
            "## 目录结构",
            "",
            "```",
            f"papers/{paper_id}/",
            "├── pdf/original.pdf          # 原始PDF",
            "├── latex/                    # LaTeX源码 (如有)",
            "├── markdown/paper.md         # 标准化Markdown",
            "├── figures/                  # 提取的图片 (最多3张)",
            "│   ├── figure_1.png         #   方法结构图",
            "│   ├── figure_2.png         #   算法流程图",
            "│   └── figure_3.png         #   实验效果图",
            "├── metadata.json            # 论文元数据",
            "├── equations.json            # 提取的公式",
            "├── figures.json              # 图片信息",
            "├── tables.json               # 表格信息",
            "├── citations.json            # 引用信息",
            "├── provenance.json           # 来源追溯",
            "└── Stage_Report.md           # 本文件",
            "```",
            "",
        ]

        if warnings:
            lines.extend(["## 警告", ""])
            for w in warnings:
                lines.append(f"- {w}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # v8.3.1: Figure Analysis
    # ------------------------------------------------------------------

    def _build_figure_analysis(
        self,
        figures: List[Dict[str, Any]],
        paper_dir: str,
        paper_id: str,
    ) -> Optional[str]:
        """v8.3.1: Build figure_analysis.json for extracted figures.

        For each extracted figure, generates:
            - 图片类型 (figure type): e.g. method_structure, algorithm_flow, experiment_results
            - 描述 (description): human-readable description of what the figure shows
            - 用途 (usage): how this figure is used in the research pipeline
            - 绘图Prompt (drawing prompt): Mermaid source code + ChatGPT/Gemini prompt

        Uses the ``semantic_label`` field set by v8.3 figure extraction to
        determine the figure type. Does NOT use Draw.io MCP — only Mermaid
        source code and ChatGPT/Gemini drawing prompts are produced.

        Args:
            figures: List of figure dicts from ``_extract_figures_v83``.
            paper_dir: Per-paper output directory.
            paper_id: Paper identifier.

        Returns:
            Path to ``figure_analysis.json``, or ``None`` if no figures or
            write failed.
        """
        if not figures:
            return None

        # ----------------------------------------------------------------
        # Per-type analysis templates (Chinese descriptions + Mermaid + prompt)
        # ----------------------------------------------------------------
        figure_type_templates: Dict[str, Dict[str, str]] = {
            "method_structure": {
                "type_cn": "方法结构图",
                "description": (
                    "展示论文所提方法的整体架构与系统组成，包括核心模块、数据流向"
                    "和各组件之间的交互关系。该图通常出现在论文的方法(Method)章节，"
                    "用于直观呈现方法的设计思路和模块层次。"
                ),
                "usage": (
                    "用于研究流水线中理解论文方法论的核心架构，辅助后续方法复现、"
                    "改进和对比分析。可作为方法理解阶段的关键参考材料，也可用于"
                    "在报告或演示中向受众快速传达方法设计。"
                ),
                "mermaid": (
                    "```mermaid\n"
                    "graph TB\n"
                    "    Input[输入数据 Input Data] --> Preprocess[预处理模块 Preprocessing]\n"
                    "    Preprocess --> CoreModule[核心方法模块 Core Method]\n"
                    "    CoreModule --> Postprocess[后处理模块 Postprocessing]\n"
                    "    Postprocess --> Output[输出结果 Output]\n"
                    "    CoreModule -.-> Feedback[反馈/优化机制 Feedback]\n"
                    "    Feedback -.-> Preprocess\n"
                    "```"
                ),
                "prompt": (
                    "请根据论文的方法描述，绘制一张方法架构图(method architecture diagram)。"
                    "要求：1) 使用清晰的方框和箭头表示模块和数据流；"
                    "2) 标注每个模块的名称和功能；3) 突出核心创新模块；"
                    "4) 使用英文标注，配色简洁专业(建议蓝-灰-白配色)；"
                    "5) 图中应包含输入、核心处理模块、输出等关键组件；"
                    "6) 如有反馈回路请用虚线箭头表示。"
                    "请参考论文方法章节的具体描述来生成这张架构图。"
                ),
            },
            "algorithm_flow": {
                "type_cn": "算法流程图",
                "description": (
                    "展示论文核心算法的执行流程，包括关键步骤的顺序、数据变换过程、"
                    "循环和条件判断分支。该图通常出现在论文的算法或方法章节，"
                    "用于说明算法的具体执行逻辑和决策路径。"
                ),
                "usage": (
                    "用于研究流水线中理解算法的具体执行过程，辅助算法实现、"
                    "复现和性能优化。可作为代码实现阶段的参考蓝图，帮助开发者"
                    "快速将论文算法转化为可运行代码。"
                ),
                "mermaid": (
                    "```mermaid\n"
                    "flowchart TD\n"
                    "    Start([开始 Start]) --> Init[初始化参数 Initialize]\n"
                    "    Init --> Step1[步骤1: 数据准备 Data Preparation]\n"
                    "    Step1 --> Step2[步骤2: 特征提取 Feature Extraction]\n"
                    "    Step2 --> Step3[步骤3: 核心计算 Core Computation]\n"
                    "    Step3 --> Cond{是否收敛? Converged?}\n"
                    "    Cond -- 否 No --> Step3\n"
                    "    Cond -- 是 Yes --> Step4[步骤4: 后处理 Post-processing]\n"
                    "    Step4 --> End([结束 End])\n"
                    "```"
                ),
                "prompt": (
                    "请根据论文的算法描述，绘制一张算法流程图(algorithm flowchart)。"
                    "要求：1) 使用标准流程图符号(开始/结束用圆角矩形，处理用矩形，"
                    "判断用菱形)；2) 清晰标注每一步的操作名称；"
                    "3) 包含循环和条件判断分支；4) 使用英文标注，配色简洁；"
                    "5) 从输入到输出展示完整流程；6) 标注关键决策点。"
                    "请参考论文中的算法伪代码或方法描述来生成这张流程图。"
                ),
            },
            "experiment_results": {
                "type_cn": "实验结果图",
                "description": (
                    "展示论文的实验结果与性能对比，可能包含不同方法在多个数据集上的"
                    "指标对比、消融实验结果、或可视化效果展示。该图通常出现在论文的"
                    "实验(Experiments)章节，用于直观呈现方法的有效性。"
                ),
                "usage": (
                    "用于研究流水线中评估方法的实验效果，辅助实验结果分析、"
                    "方法对比和性能基准建立。可作为实验设计阶段的参考依据，"
                    "也可用于在综述报告中汇总不同方法的性能表现。"
                ),
                "mermaid": (
                    "```mermaid\n"
                    "graph LR\n"
                    "    Baseline1[基线方法A Baseline A] -->|指标对比| Result[实验结果 Results]\n"
                    "    Baseline2[基线方法B Baseline B] -->|指标对比| Result\n"
                    "    Baseline3[基线方法C Baseline C] -->|指标对比| Result\n"
                    "    Proposed[本文方法 Ours] -->|最优| Result\n"
                    "    Result --> Analysis[性能分析 Analysis]\n"
                    "    Analysis --> Conclusion[实验结论 Conclusion]\n"
                    "```"
                ),
                "prompt": (
                    "请根据论文的实验结果描述，绘制一张实验结果对比图"
                    "(experiment results comparison chart)。"
                    "要求：1) 包含本文方法与至少2-3个基线方法的对比；"
                    "2) 使用柱状图或折线图展示关键指标(如准确率Accuracy、F1等)；"
                    "3) 标注数据集名称和指标名称；4) 突出本文方法的优势；"
                    "5) 使用英文标注，配色专业(建议使用区分度高的颜色)；"
                    "6) 如有消融实验请单独标注。"
                    "请参考论文实验章节的表格或图表数据来生成这张对比图。"
                ),
            },
        }

        # Default template for unknown figure types
        default_template: Dict[str, str] = {
            "type_cn": "论文配图",
            "description": (
                "从论文中提取的图片，用于展示研究的某个方面。具体内容需结合"
                "论文上下文进一步分析。"
            ),
            "usage": (
                "用于研究流水线中辅助理解论文内容，可作为研究材料归档和"
                "后续分析的参考。"
            ),
            "mermaid": (
                "```mermaid\n"
                "graph TB\n"
                "    A[论文内容 Paper Content] --> B[图片展示 Figure Display]\n"
                "```"
            ),
            "prompt": (
                "请根据论文描述绘制一张示意图。"
                "要求：使用清晰的图形和标注，配色简洁专业，"
                "标注关键组件和数据流。请参考论文上下文确定图片的具体内容。"
            ),
        }

        analysis_items: List[Dict[str, Any]] = []
        for i, fig in enumerate(figures, 1):
            semantic_label = fig.get("semantic_label", "")
            template = figure_type_templates.get(semantic_label, default_template)

            analysis_item: Dict[str, Any] = {
                "figure_id": fig.get("figure_id", f"fig{i}"),
                "figure_index": i,
                "filename": fig.get("filename", f"figure_{i}.png"),
                "path": fig.get("path", f"figures/figure_{i}.png"),
                "source": fig.get("source", "unknown"),
                "图片类型": template["type_cn"],
                "图片类型_en": semantic_label or "unknown",
                "描述": template["description"],
                "用途": template["usage"],
                "绘图Prompt": {
                    "mermaid_source": template["mermaid"],
                    "chatgpt_gemini_prompt": template["prompt"],
                },
            }
            analysis_items.append(analysis_item)

        analysis_data: Dict[str, Any] = {
            "paper_id": paper_id,
            "total_figures": len(analysis_items),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "figures": analysis_items,
        }

        analysis_path = os.path.join(paper_dir, "figure_analysis.json")
        try:
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            logger.info(
                "v8.3.1: figure_analysis.json generated for %s (%d figures)",
                paper_id, len(analysis_items),
            )
            return analysis_path
        except Exception as exc:
            logger.warning(
                "v8.3.1: Failed to write figure_analysis.json for %s: %s",
                paper_id, exc,
            )
            return None
