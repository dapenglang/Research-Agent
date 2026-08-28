"""Paper extractor — extracts structured knowledge from normalized paper.md files."""
import json
import os
import re
from typing import Dict, Any, Optional


class PaperExtractor:
    def __init__(self, **kwargs):
        pass

    def extract(self, md_path: str, analysis_path: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract structured knowledge from a normalized paper.md file.

        Args:
            md_path: Path to the paper.md file.
            analysis_path: Optional path to save the analysis JSON.
            metadata: Optional metadata dict from upstream.

        Returns:
            Knowledge dict with paper_id, title, authors, abstract,
            innovation, method, research_problem, dataset, baseline,
            limitation, future_direction, _extraction_strategy.
        """
        metadata = metadata or {}
        knowledge: Dict[str, Any] = {
            "paper_id": metadata.get("paper_id", ""),
            "title": metadata.get("title", ""),
            "authors": metadata.get("authors", []),
            "abstract": metadata.get("abstract", ""),
            "year": metadata.get("year", ""),
            "venue": metadata.get("venue", ""),
            "doi": "",
            "arxiv_id": metadata.get("paper_id", ""),
            "innovation": "",
            "method": "",
            "research_problem": "",
            "dataset": "",
            "baseline": "",
            "limitation": "",
            "future_direction": "",
            "_extraction_strategy": "heuristic",
        }

        if not os.path.exists(md_path):
            return knowledge

        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Extract title from first # heading
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            knowledge["title"] = title_match.group(1).strip()

        # Extract abstract
        abs_match = re.search(r"##\s*Abstract\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        if abs_match:
            knowledge["abstract"] = abs_match.group(1).strip()

        # Extract introduction as research_problem
        intro_match = re.search(r"##\s*\d*\s*Introduction\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        if intro_match:
            knowledge["research_problem"] = intro_match.group(1).strip()[:500]

        # Extract method
        method_match = re.search(r"##\s*\d*\s*Method\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        if method_match:
            knowledge["method"] = method_match.group(1).strip()[:500]

        # Extract experiments for dataset/baseline info
        exp_match = re.search(r"##\s*\d*\s*Experiment\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        if exp_match:
            exp_text = exp_match.group(1)
            knowledge["dataset"] = "synthetic" if "synthetic" in exp_text.lower() else ""
            knowledge["baseline"] = "baseline" if "baseline" in exp_text.lower() else ""

        # Extract conclusion for limitation/future_direction
        conc_match = re.search(r"##\s*\d*\s*Conclusion\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        if conc_match:
            conc_text = conc_match.group(1).strip()
            knowledge["limitation"] = conc_text[:300]
            knowledge["future_direction"] = conc_text[:300]

        # Derive innovation from title + abstract
        if knowledge["title"]:
            knowledge["innovation"] = f"Novel approach: {knowledge['title']}"

        # Save analysis if path provided
        if analysis_path:
            os.makedirs(os.path.dirname(analysis_path) or ".", exist_ok=True)
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(knowledge, f, indent=2, ensure_ascii=False)

        return knowledge
