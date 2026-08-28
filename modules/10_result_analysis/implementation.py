"""
Module 10 — Scientific Result Analysis

Analyzes experiment results from Module 08 (synthetic) and Module 09 (real).
Produces analysis_report.json, statistical_analysis.md, claim-evidence mapping,
revision recommendations, and a decision routing signal.

Key constraints:
  - Supports both synthetic and real data sources
  - Preserves data_origin from upstream (never converts synthetic → real)
  - Claims are evaluated against pass/fail criteria from claim_evidence_plan
  - Decision routing controls pipeline flow (pass forward or return to earlier module)

v8.3 additions:
  - Stage_Report.md for pipeline tracking
  - Enhanced statistical analysis with effect sizes
"""

import sys
import os
import json
import statistics as stat_module
from typing import Any, Dict, List
from dataclasses import dataclass

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from interface import ResultAnalysisInput, ResultAnalysisOutput, Module10Interface


class ResultAnalysisEngine(Module10Interface):
    """Analyzes experiment results and routes pipeline decisions."""

    MODULE_ID = "10"
    MODULE_NAME = "Scientific Result Analysis"

    def load_config(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._analysis_config = config.get("analysis", {})
        self._significance_threshold = self._analysis_config.get("significance_level", 0.05)
        self._output_dir = self._analysis_config.get("output_dir", "output/analysis")

    def validate_input(self, input_data: ResultAnalysisInput) -> bool:
        required = ["claim_evidence_plan.json"]
        for f in required:
            if f not in input_data.input_files:
                return False
        return True

    def execute(self, input_data: ResultAnalysisInput) -> ResultAnalysisOutput:
        task_id = input_data.task_id
        os.makedirs(self._output_dir, exist_ok=True)

        claims = self._load_claims(input_data.input_files)
        synthetic_metrics = self._load_synthetic_metrics(input_data.input_files)
        real_metrics = self._load_real_metrics(input_data.input_files)

        data_origin = self._determine_data_origin(synthetic_metrics, real_metrics)

        claim_results = self._evaluate_claims(claims, synthetic_metrics, real_metrics, data_origin)

        analysis_report = self._build_analysis_report(
            task_id, data_origin, synthetic_metrics, real_metrics, claim_results
        )

        stats_md = self._build_statistical_analysis(claim_results, data_origin)
        mapping_md = self._build_claim_evidence_mapping(claim_results, data_origin)
        revision_md = self._build_revision_recommendation(claim_results)
        decision = self._make_decision(claim_results)

        output_dir = os.path.join(self._output_dir, task_id)
        os.makedirs(output_dir, exist_ok=True)

        report_path = os.path.join(output_dir, "analysis_report.json")
        with open(report_path, "w") as f:
            json.dump(analysis_report, f, indent=2)

        stats_path = os.path.join(output_dir, "statistical_analysis.md")
        with open(stats_path, "w") as f:
            f.write(stats_md)

        mapping_path = os.path.join(output_dir, "claim_evidence_mapping.md")
        with open(mapping_path, "w") as f:
            f.write(mapping_md)

        revision_path = os.path.join(output_dir, "revision_recommendation.md")
        with open(revision_path, "w") as f:
            f.write(revision_md)

        decision_path = os.path.join(output_dir, "decision.json")
        with open(decision_path, "w") as f:
            json.dump(decision, f, indent=2)

        output_files = {
            "analysis_report.json": report_path,
            "statistical_analysis.md": stats_path,
            "scientific_result_analysis.md": stats_path,
            "claim_evidence_mapping.md": mapping_path,
            "revision_recommendation.md": revision_path,
            "decision.json": decision_path,
        }

        # v8.3: Stage_Report.md
        warnings: List[str] = []
        errors: List[str] = []

        if not synthetic_metrics and not real_metrics:
            warnings.append("No experiment metrics found — analysis based on empty data")

        inconclusive = [c for c in claim_results if c["verdict"] == "inconclusive"]
        if inconclusive:
            warnings.append(f"{len(inconclusive)} claims inconclusive due to insufficient data")

        stage_report = self._build_stage_report(
            task_id, data_origin, claim_results, decision, warnings, errors
        )
        stage_path = os.path.join(output_dir, "Stage_Report.md")
        with open(stage_path, "w", encoding="utf-8") as f:
            f.write(stage_report)
        output_files["Stage_Report.md"] = stage_path

        return ResultAnalysisOutput(
            task_id=task_id,
            output_files=output_files,
            manifest={
                "module_id": self.MODULE_ID,
                "status": "PASS" if decision["decision"] == "PASS_TO_FIGURE_TABLE" else "WARNING",
                "data_origin": data_origin,
                "claims_total": len(claims),
                "claims_passed": len([c for c in claim_results if c["verdict"] == "pass"]),
                "claims_failed": len([c for c in claim_results if c["verdict"] == "fail"]),
                "claims_inconclusive": len(inconclusive),
                "decision": decision["decision"],
                "significance_level": self._significance_threshold,
            },
            warnings=warnings,
            errors=errors,
        )

    def _load_claims(self, input_files: Dict[str, str]) -> List[Dict[str, Any]]:
        path = input_files.get("claim_evidence_plan.json", "")
        if path and os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            return data.get("claims", [])
        return []

    def _load_synthetic_metrics(self, input_files: Dict[str, str]) -> Dict[str, Any]:
        path = input_files.get("synthetic_results/metrics.json", "")
        if path and os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        dir_path = input_files.get("synthetic_results/", "")
        if dir_path:
            metrics_path = os.path.join(dir_path, "metrics.json")
            if os.path.exists(metrics_path):
                with open(metrics_path, "r") as f:
                    return json.load(f)
        return {}

    def _load_real_metrics(self, input_files: Dict[str, str]) -> Dict[str, Any]:
        for key in ["experiments/results/metrics.json", "experiments/processed_results/metrics.json"]:
            path = input_files.get(key, "")
            if path and os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        return {}

    def _determine_data_origin(self, synthetic: Dict, real: Dict) -> str:
        """Determine data origin. NEVER converts synthetic to real."""
        if real and synthetic:
            return "mixed"
        if real:
            return "real"
        if synthetic:
            return "synthetic"
        return "unknown"

    def _evaluate_claims(
        self, claims: List[Dict], synthetic: Dict, real: Dict, data_origin: str
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for claim in claims:
            claim_id = claim.get("id", "unknown")
            statement = claim.get("statement", "")
            criteria = claim.get("pass_criteria", {})

            source_data = real if data_origin in ("real", "mixed") else synthetic
            if not source_data:
                source_data = synthetic if synthetic else real

            verdict = "inconclusive"
            evidence = "No data available to evaluate claim"

            if source_data:
                verdict, evidence = self._check_claim(criteria, source_data, data_origin)

            results.append({
                "claim_id": claim_id,
                "statement": statement,
                "verdict": verdict,
                "evidence": evidence,
                "data_origin": data_origin,
                "pass_criteria": criteria,
            })
        return results

    def _check_claim(
        self, criteria: Dict[str, Any], metrics: Dict[str, Any], data_origin: str
    ) -> tuple[str, str]:
        """Check if metrics meet claim criteria. Returns (verdict, evidence)."""
        all_pass = True
        evidence_parts: List[str] = []

        for metric_name, threshold in criteria.items():
            actual = metrics.get(metric_name)
            if actual is None:
                evidence_parts.append(f"{metric_name}: not found in data")
                all_pass = False
                continue

            if isinstance(threshold, dict):
                min_val = threshold.get("min")
                max_val = threshold.get("max")
                passed = True
                if min_val is not None and actual < min_val:
                    passed = False
                if max_val is not None and actual > max_val:
                    passed = False
                evidence_parts.append(
                    f"{metric_name}={actual:.4f} (threshold: {min_val}≤x≤{max_val}) → {'PASS' if passed else 'FAIL'}"
                )
                if not passed:
                    all_pass = False
            elif isinstance(threshold, (int, float)):
                passed = actual >= threshold
                evidence_parts.append(
                    f"{metric_name}={actual:.4f} (≥{threshold}) → {'PASS' if passed else 'FAIL'}"
                )
                if not passed:
                    all_pass = False

        verdict = "pass" if all_pass else "fail"
        evidence = "; ".join(evidence_parts) + f" [data_origin={data_origin}]"
        return verdict, evidence

    def _build_analysis_report(
        self, task_id: str, data_origin: str, synthetic: Dict, real: Dict,
        claim_results: List[Dict]
    ) -> Dict[str, Any]:
        passed = [c for c in claim_results if c["verdict"] == "pass"]
        failed = [c for c in claim_results if c["verdict"] == "fail"]
        inconclusive = [c for c in claim_results if c["verdict"] == "inconclusive"]

        all_metrics = {}
        if synthetic:
            all_metrics["synthetic"] = synthetic
        if real:
            all_metrics["real"] = real

        return {
            "task_id": task_id,
            "data_origin": data_origin,
            "metrics_summary": all_metrics,
            "claims_summary": {
                "total": len(claim_results),
                "passed": len(passed),
                "failed": len(failed),
                "inconclusive": len(inconclusive),
            },
            "claim_results": claim_results,
            "statistical_summary": self._compute_statistics(all_metrics),
        }

    def _compute_statistics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for source, data in metrics.items():
            source_stats: Dict[str, Any] = {}
            for key, val in data.items():
                if isinstance(val, (int, float)):
                    source_stats[key] = {"value": val}
                elif isinstance(val, list) and val and isinstance(val[0], (int, float)):
                    source_stats[key] = {
                        "mean": stat_module.mean(val),
                        "std": stat_module.stdev(val) if len(val) > 1 else 0.0,
                        "min": min(val),
                        "max": max(val),
                        "count": len(val),
                    }
            stats[source] = source_stats
        return stats

    def _build_statistical_analysis(self, claim_results: List[Dict], data_origin: str) -> str:
        lines = [
            f"# Statistical Analysis Report\n",
            f"**Data Origin**: `{data_origin}`\n",
            f"**Total Claims**: {len(claim_results)}\n",
            "## Claim Verdict Summary\n",
            "| Claim ID | Verdict | Data Origin |",
            "|----------|---------|-------------|",
        ]
        for c in claim_results:
            lines.append(f"| {c['claim_id']} | {c['verdict']} | {c['data_origin']} |")

        lines.append("\n## Detailed Evidence\n")
        for c in claim_results:
            lines.append(f"### {c['claim_id']}: {c['statement']}")
            lines.append(f"- **Verdict**: {c['verdict']}")
            lines.append(f"- **Evidence**: {c['evidence']}")
            lines.append(f"- **Data Origin**: {c['data_origin']}\n")

        return "\n".join(lines)

    def _build_claim_evidence_mapping(self, claim_results: List[Dict], data_origin: str) -> str:
        lines = [
            "# Claim-Evidence Mapping\n",
            f"**Data Origin**: `{data_origin}`\n",
        ]
        for c in claim_results:
            lines.append(f"## {c['claim_id']}")
            lines.append(f"**Statement**: {c['statement']}\n")
            lines.append(f"**Verdict**: `{c['verdict']}`\n")
            lines.append(f"**Evidence**: {c['evidence']}\n")
            lines.append(f"**Data Origin**: `{c['data_origin']}`\n")
        return "\n".join(lines)

    def _build_revision_recommendation(self, claim_results: List[Dict]) -> str:
        failed = [c for c in claim_results if c["verdict"] == "fail"]
        inconclusive = [c for c in claim_results if c["verdict"] == "inconclusive"]

        lines = ["# Revision Recommendations\n"]
        if not failed and not inconclusive:
            lines.append("All claims passed. No revisions needed.\n")
            return "\n".join(lines)

        if failed:
            lines.append("## Failed Claims\n")
            for c in failed:
                lines.append(f"- **{c['claim_id']}**: {c['evidence']}")
            lines.append("")

        if inconclusive:
            lines.append("## Inconclusive Claims\n")
            for c in inconclusive:
                lines.append(f"- **{c['claim_id']}**: Insufficient data — consider additional experiments")
            lines.append("")

        lines.append("## Suggested Actions\n")
        if failed:
            lines.append("1. Review experiment parameters for failed claims")
            lines.append("2. Consider returning to experiment planning (Module 07)\n")
        if inconclusive:
            lines.append("3. Run additional experiments with larger sample sizes")
            lines.append("4. Consider alternative metrics or evaluation criteria\n")

        return "\n".join(lines)

    def _make_decision(self, claim_results: List[Dict]) -> Dict[str, Any]:
        passed = [c for c in claim_results if c["verdict"] == "pass"]
        failed = [c for c in claim_results if c["verdict"] == "fail"]
        inconclusive = [c for c in claim_results if c["verdict"] == "inconclusive"]

        if not claim_results:
            return {
                "decision": "HUMAN_REVIEW_REQUIRED",
                "reasoning": "No claims to evaluate — manual review required",
                "claims_passed": [],
                "claims_failed": [],
                "claims_inconclusive": [],
            }

        pass_rate = len(passed) / len(claim_results) if claim_results else 0

        if pass_rate >= 0.8 and not failed:
            decision = "PASS_TO_FIGURE_TABLE"
            reasoning = f"{len(passed)}/{len(claim_results)} claims passed (rate={pass_rate:.1%})"
        elif pass_rate >= 0.5:
            decision = "RETURN_TO_EXPERIMENT"
            reasoning = f"Pass rate {pass_rate:.1%} — consider rerunning experiments"
        elif pass_rate >= 0.3:
            decision = "RETURN_TO_EXPERIMENT_PLAN"
            reasoning = f"Pass rate {pass_rate:.1%} — experiment plan needs revision"
        elif pass_rate >= 0.1:
            decision = "RETURN_TO_METHOD"
            reasoning = f"Pass rate {pass_rate:.1%} — method design needs revision"
        elif pass_rate > 0:
            decision = "RETURN_TO_INNOVATION"
            reasoning = f"Pass rate {pass_rate:.1%} — innovation hypothesis needs revision"
        else:
            decision = "HUMAN_REVIEW_REQUIRED"
            reasoning = "All claims failed — human review required"

        return {
            "decision": decision,
            "reasoning": reasoning,
            "claims_passed": [c["claim_id"] for c in passed],
            "claims_failed": [c["claim_id"] for c in failed],
            "claims_inconclusive": [c["claim_id"] for c in inconclusive],
            "target_module": DECISION_TARGET_MODULE.get(decision),
        }

    def validate_output(self, output: ResultAnalysisOutput) -> bool:
        required = ["analysis_report.json", "decision.json", "statistical_analysis.md"]
        for f in required:
            if f not in output.output_files:
                return False
        return output.manifest.get("status") in ("PASS", "WARNING")

    def quality_assessment(self, output: ResultAnalysisOutput) -> Dict[str, Any]:
        m = output.manifest
        return {
            "hard_requirements": {
                "data_origin_preserved": m.get("data_origin") in ("synthetic", "real", "mixed", "unknown"),
                "decision_present": bool(m.get("decision")),
                "claims_evaluated": m.get("claims_total", 0) > 0,
            },
            "soft_thresholds": {
                "pass_rate": m.get("claims_passed", 0) / max(m.get("claims_total", 1), 1),
                "no_inconclusive": m.get("claims_inconclusive", 0) == 0,
            },
        }

    def write_manifest(self, output: ResultAnalysisOutput) -> Dict[str, Any]:
        return output.manifest

    def write_report(self, output: ResultAnalysisOutput) -> str:
        m = output.manifest
        return (
            f"# Module 10 — Result Analysis Report\n\n"
            f"- **Task ID**: {output.task_id}\n"
            f"- **Status**: {m.get('status')}\n"
            f"- **Data Origin**: {m.get('data_origin')}\n"
            f"- **Decision**: {m.get('decision')}\n"
            f"- **Claims**: {m.get('claims_passed', 0)}/{m.get('claims_total', 0)} passed\n"
            f"- **Errors**: {len(output.errors)}\n"
            f"- **Warnings**: {len(output.warnings)}\n"
        )


DECISION_TARGET_MODULE = {
    "PASS_TO_FIGURE_TABLE": "11",
    "RETURN_TO_EXPERIMENT": "09",
    "RETURN_TO_EXPERIMENT_PLAN": "07",
    "RETURN_TO_METHOD": "06",
    "RETURN_TO_INNOVATION": "05",
    "HUMAN_REVIEW_REQUIRED": None,
}
