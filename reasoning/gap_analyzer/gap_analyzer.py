"""Gap analyzer — identifies research gaps using LLM or heuristic methods."""
import json
import os
from typing import Dict, List, Any, Optional


FIELD_KEYWORDS: Dict[str, List[str]] = {
    "methodology": ["method", "approach", "framework", "algorithm", "architecture", "model", "technique"],
    "dataset": ["dataset", "benchmark", "corpus", "data", "evaluation set"],
    "baseline": ["baseline", "comparison", "state-of-the-art", "sota", "prior work"],
    "evaluation": ["metric", "accuracy", "precision", "recall", "f1", "bleu", "score"],
    "limitation": ["limitation", "drawback", "challenge", "issue", "problem", "shortcoming"],
    "future_direction": ["future", "extension", "next step", "further work", "open problem"],
}

TECHNIQUE_KEYWORDS: Dict[str, List[str]] = {
    "deep_learning": ["neural network", "deep learning", "cnn", "rnn", "transformer", "attention"],
    "optimization": ["optimization", "gradient", "sgd", "adam", "loss function", "convergence"],
    "data_augmentation": ["augmentation", "data augmentation", "preprocessing", "normalization"],
    "adversarial": ["adversarial", "attack", "defense", "robustness", "perturbation"],
    "transfer_learning": ["transfer", "pretrain", "fine-tune", "fine tune", "domain adaptation"],
    "reinforcement_learning": ["reinforcement", "reward", "policy", "rl", "agent"],
}


class GapAnalyzer:
    def __init__(self, llm_provider=None, **kwargs):
        self.llm_provider = llm_provider

    def analyze(self, papers: List[Dict] = None, research_context: Dict = None,
                paper_database_path: str = None, output_path: str = None,
                **kwargs) -> Dict[str, Any]:
        """Analyze research gaps from a paper database.

        Can be called with either (papers, research_context) or
        (paper_database_path, output_path) signature.

        If output_path is provided, writes a markdown landscape report.
        """
        # Load papers from database if path provided
        if paper_database_path and os.path.exists(paper_database_path):
            with open(paper_database_path, "r", encoding="utf-8") as f:
                db = json.load(f)
            if isinstance(db, dict):
                papers = list(db.values())
            elif isinstance(db, list):
                papers = db
        elif papers is None:
            papers = []

        research_context = research_context or {}
        topic = research_context.get("topic", "unknown")

        # Categorize papers by field
        categories: Dict[str, List[str]] = {}
        for paper in papers:
            text = (paper.get("title", "") + " " + paper.get("abstract", "") +
                    " " + paper.get("method", "")).lower()
            for field, keywords in FIELD_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    categories.setdefault(field, []).append(
                        paper.get("paper_id", paper.get("title", ""))
                    )

        # Identify gaps
        gaps = []
        if self.llm_provider and self.llm_provider.is_available():
            try:
                prompt = f"Analyze research gaps based on {len(papers)} papers in {topic}."
                result = self.llm_provider.generate(prompt)
                gaps.append({"gap_id": "gap_1", "description": result[:500],
                             "severity": "medium", "field": "general"})
            except Exception:
                gaps.append({"gap_id": "gap_1",
                             "description": f"LLM analysis failed for {topic}",
                             "severity": "low", "field": "general"})
        else:
            # Heuristic gap detection
            for field in FIELD_KEYWORDS:
                count = len(categories.get(field, []))
                if count < 3:
                    gaps.append({
                        "gap_id": f"gap_{field}",
                        "description": f"Insufficient coverage in {field} ({count} papers)",
                        "severity": "high" if count == 0 else "medium",
                        "field": field,
                    })

        result = {"gaps": gaps, "categories": categories, "analysis": "Gap analysis completed"}

        # Write landscape report if output path provided
        if output_path:
            self._write_landscape(output_path, papers, gaps, categories, topic)

        return result

    @staticmethod
    def _write_landscape(path: str, papers: List[Dict], gaps: List[Dict],
                         categories: Dict[str, List[str]], topic: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        lines = [
            f"# Research Landscape: {topic}",
            "",
            f"## Overview",
            "",
            f"- Total papers analyzed: {len(papers)}",
            f"- Gaps identified: {len(gaps)}",
            "",
            "## Paper Categories",
            "",
        ]
        for field, pids in categories.items():
            lines.append(f"### {field.title()} ({len(pids)} papers)")
            for pid in pids:
                lines.append(f"- {pid}")
            lines.append("")

        lines.append("## Identified Gaps")
        lines.append("")
        for gap in gaps:
            lines.append(f"### {gap.get('gap_id', 'N/A')}: {gap.get('description', 'N/A')}")
            lines.append(f"- Severity: {gap.get('severity', 'unknown')}")
            lines.append(f"- Field: {gap.get('field', 'general')}")
            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
