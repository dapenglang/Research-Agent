"""Quality checker — evaluates extracted paper knowledge for completeness."""
import json
import os
from typing import Dict, Any, List


class QualityChecker:
    def __init__(self, **kwargs):
        pass

    def check(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check the quality of extracted paper knowledge.

        Returns a dict with score, overall_pass, and per-field checks.
        """
        required_fields = ["title", "abstract", "method", "innovation"]
        field_checks = {f: bool(paper_data.get(f)) for f in required_fields}
        passed = sum(field_checks.values())
        total = len(required_fields)
        score = passed / total if total > 0 else 0.0

        issues = [f"Missing field: {f}" for f, ok in field_checks.items() if not ok]

        return {
            "score": round(score, 2),
            "overall_pass": score >= 0.5,
            "completeness": round(score, 2),
            "has_abstract": field_checks.get("abstract", False),
            "has_method": field_checks.get("method", False),
            "field_checks": field_checks,
            "issues": issues,
        }

    def save_report(self, reports: List[Dict[str, Any]], path: str) -> None:
        """Save quality reports to a JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reports, f, indent=2, ensure_ascii=False)
