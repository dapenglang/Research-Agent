"""
Module 07 -- Experiment Planning
Implementation (facade/adapter pattern).

Wraps the existing reasoning component:
  - reasoning.experiment_designer.experiment_designer.ExperimentDesigner

Produces:
  - experiment_plan.md
  - experiment_matrix.yaml
  - claim_evidence_plan.json
  - paper_figure_plan.yaml

v8.3 additions:
  - experiment_plan.yaml (structured experiment plan with ablation/baseline lists)
  - Stage_Report.md (Chinese stage report with task metadata and completion status)
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
# Project-root bootstrap.
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from reasoning.experiment_designer.experiment_designer import ExperimentDesigner

from .interface import (
    Module07Interface,
    ExperimentPlanningInput,
    ExperimentPlanningOutput,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM provider adapter.
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
# Module 07 implementation
# ---------------------------------------------------------------------------

class ExperimentPlanningModule(Module07Interface):
    """Facade that wraps ExperimentDesigner."""

    MODULE_ID = "07"
    MODULE_NAME = "Experiment Planning"
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
        logger.info("Module 07 config loaded: %s", list(self._config.keys()))

    def validate_input(self, input_data: ExperimentPlanningInput) -> bool:
        """Validate that all required inputs are present."""
        if not input_data.input_files.get("method_spec.json"):
            logger.error("Missing required input file: method_spec.json")
            return False
        return True

    def execute(
        self, input_data: ExperimentPlanningInput
    ) -> ExperimentPlanningOutput:
        """Run the experiment-planning pipeline."""
        warnings: List[str] = []
        errors: List[str] = []
        output_files: Dict[str, str] = {}

        output_dir = self._config.get(
            "output_dir",
            os.path.join(tempfile.gettempdir(), f"module07_{input_data.task_id}"),
        )
        os.makedirs(output_dir, exist_ok=True)

        # ----------------------------------------------------------
        # 1. Load method spec and prepare method proposal file.
        # ----------------------------------------------------------
        method_spec_path = input_data.input_files.get("method_spec.json")
        method_spec = self._load_json(method_spec_path)

        # ExperimentDesigner expects a method proposal markdown file.
        method_proposal_path = os.path.join(output_dir, "_method_proposal.md")
        self._write_method_proposal(method_proposal_path, method_spec)

        # Optional: read hypothesis path from upstream context.
        hypothesis_path = input_data.input_files.get("hypothesis_report.md")
        if not hypothesis_path or not os.path.exists(hypothesis_path):
            hypothesis_path = None

        # ----------------------------------------------------------
        # 2. ExperimentDesigner -- generate experiment plan.
        # ----------------------------------------------------------
        experiment_designer = ExperimentDesigner(llm_provider=self._llm_provider)
        raw_experiment_path = os.path.join(output_dir, "_experiment_design.md")
        try:
            experiment_designer.design(
                method_proposal_path=method_proposal_path,
                output_path=raw_experiment_path,
                hypothesis_path=hypothesis_path,
            )
        except Exception as exc:
            logger.warning("ExperimentDesigner failed: %s", exc)
            warnings.append(f"Experiment design error: {exc}")
            self._write_minimal_experiment_plan(raw_experiment_path, method_spec)

        # Read experiment design content.
        experiment_content = ""
        if os.path.exists(raw_experiment_path):
            try:
                with open(raw_experiment_path, "r", encoding="utf-8") as f:
                    experiment_content = f.read()
            except Exception:
                experiment_content = ""

        # ----------------------------------------------------------
        # 3. Produce output files.
        # ----------------------------------------------------------
        # experiment_plan.md
        plan_path = os.path.join(output_dir, "experiment_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(experiment_content if experiment_content else
                    "# Experiment Plan\n\nNo experiment plan generated.")
        output_files["experiment_plan.md"] = plan_path

        # experiment_matrix.yaml
        matrix = self._build_experiment_matrix(experiment_content, method_spec)
        matrix_path = os.path.join(output_dir, "experiment_matrix.yaml")
        with open(matrix_path, "w", encoding="utf-8") as f:
            f.write(self._dict_to_yaml(matrix))
        output_files["experiment_matrix.yaml"] = matrix_path

        # claim_evidence_plan.json
        claim_plan = self._build_claim_evidence_plan(experiment_content, matrix)
        claim_path = os.path.join(output_dir, "claim_evidence_plan.json")
        with open(claim_path, "w", encoding="utf-8") as f:
            json.dump(claim_plan, f, ensure_ascii=False, indent=2)
        output_files["claim_evidence_plan.json"] = claim_path

        # paper_figure_plan.yaml
        figure_plan = self._build_paper_figure_plan(experiment_content, matrix)
        figure_path = os.path.join(output_dir, "paper_figure_plan.yaml")
        with open(figure_path, "w", encoding="utf-8") as f:
            f.write(self._dict_to_yaml(figure_plan))
        output_files["paper_figure_plan.yaml"] = figure_path

        # experiment_plan.yaml (v8.3)
        experiment_plan = self._build_experiment_plan_yaml(
            input_data.task_id, method_spec, matrix
        )
        experiment_plan_path = os.path.join(output_dir, "experiment_plan.yaml")
        with open(experiment_plan_path, "w", encoding="utf-8") as f:
            f.write(self._dict_to_yaml(experiment_plan))
        output_files["experiment_plan.yaml"] = experiment_plan_path

        # Stage_Report.md (v8.3)
        stage_report = self._build_stage_report(
            input_data.task_id, method_spec, matrix, warnings, errors
        )
        stage_report_path = os.path.join(output_dir, "Stage_Report.md")
        with open(stage_report_path, "w", encoding="utf-8") as f:
            f.write(stage_report)
        output_files["Stage_Report.md"] = stage_report_path

        output = ExperimentPlanningOutput(
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

    def validate_output(self, output: ExperimentPlanningOutput) -> bool:
        """Validate that all required outputs are present."""
        required = ["experiment_plan.md", "experiment_matrix.yaml",
                     "claim_evidence_plan.json", "paper_figure_plan.yaml"]
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
        self, output: ExperimentPlanningOutput
    ) -> Dict[str, Any]:
        details: Dict[str, Any] = {}

        plan_path = output.output_files.get("experiment_plan.md", "")
        plan_nonempty = (
            os.path.exists(plan_path) and os.path.getsize(plan_path) > 0
        )
        details["plan_nonempty"] = plan_nonempty

        matrix_path = output.output_files.get("experiment_matrix.yaml", "")
        matrix_nonempty = (
            os.path.exists(matrix_path) and os.path.getsize(matrix_path) > 0
        )
        details["matrix_nonempty"] = matrix_nonempty

        all_outputs_exist = all(
            os.path.exists(p) and os.path.getsize(p) > 0
            for p in output.output_files.values()
        )
        details["all_outputs_nonempty"] = all_outputs_exist

        passed = plan_nonempty and matrix_nonempty and all_outputs_exist

        return {
            "passed": passed,
            "details": details,
            "assessed_at": datetime.now().isoformat(),
        }

    def write_manifest(
        self, output: ExperimentPlanningOutput
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

    def write_report(self, output: ExperimentPlanningOutput) -> str:
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
    def _load_json(path: Optional[str]) -> Dict[str, Any]:
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_method_proposal(
        self, path: str, method_spec: Dict[str, Any]
    ) -> None:
        """Write a method proposal markdown from the method spec."""
        lines = [
            "# Method Proposal",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Method Name",
            "",
            method_spec.get("method_name", "Proposed Method"),
            "",
            "## Description",
            "",
            method_spec.get("description", "Method description from spec."),
            "",
            "## Components",
            "",
        ]
        for comp in method_spec.get("components", []):
            lines.append(f"- **{comp.get('name', 'N/A')}** ({comp.get('type', 'N/A')})")
            params = comp.get("params", {})
            if params:
                for k, v in params.items():
                    lines.append(f"  - {k}: {v}")

        lines.extend([
            "",
            "## Input Schema",
            "",
            f"- {method_spec.get('input_schema', {})}",
            "",
            "## Output Schema",
            "",
            f"- {method_spec.get('output_schema', {})}",
        ])

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _write_minimal_experiment_plan(
        self, path: str, method_spec: Dict[str, Any]
    ) -> None:
        lines = [
            "# Experiment Plan",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Datasets",
            "",
            "- Dataset to be determined based on the research domain.",
            "",
            "## Models",
            "",
            f"- {method_spec.get('method_name', 'Proposed Method')}",
            "",
            "## Baselines",
            "",
            "- Baseline methods to be determined.",
            "",
            "## Evaluation Metrics",
            "",
            "- Metrics to be determined based on the task.",
            "",
            "## Ablation Study",
            "",
            "- Ablation experiments to be designed.",
            "",
            "## Expected Results",
            "",
            "- Expected results based on theoretical analysis.",
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _build_experiment_matrix(
        self,
        experiment_content: str,
        method_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build experiment_matrix.yaml conforming to schema."""
        experiments: List[Dict[str, Any]] = []

        # Extract datasets from content.
        datasets = self._extract_section_items(experiment_content, "Dataset")
        # Extract models.
        models = self._extract_section_items(experiment_content, "Model")
        # Extract baselines.
        baselines = self._extract_section_items(experiment_content, "Baseline")
        # Extract metrics.
        metrics = self._extract_section_items(experiment_content, "Metric")

        if not datasets:
            datasets = ["default_dataset"]
        if not models:
            models = [method_spec.get("method_name", "ProposedMethod")]
        if not baselines:
            baselines = ["baseline_1"]
        if not metrics:
            metrics = ["accuracy"]

        exp_id = 1

        # Main experiments: model x dataset.
        for model in models[:3]:
            for ds in datasets[:3]:
                experiments.append({
                    "id": f"exp_{exp_id:03d}",
                    "name": f"{model} on {ds}",
                    "type": "main",
                    "data_origin": "real",
                    "parameters": {
                        "model": model,
                        "dataset": ds,
                        "metrics": metrics,
                    },
                    "expected_runtime": "TBD",
                    "claims_addressed": [f"claim_{exp_id:03d}"],
                })
                exp_id += 1

        # Baseline experiments.
        for baseline in baselines[:3]:
            for ds in datasets[:2]:
                experiments.append({
                    "id": f"exp_{exp_id:03d}",
                    "name": f"{baseline} on {ds}",
                    "type": "baseline",
                    "data_origin": "real",
                    "parameters": {
                        "model": baseline,
                        "dataset": ds,
                        "metrics": metrics,
                    },
                    "expected_runtime": "TBD",
                    "claims_addressed": [f"claim_{exp_id:03d}"],
                })
                exp_id += 1

        # Ablation experiments.
        components = method_spec.get("components", [])
        for comp in components[:3]:
            experiments.append({
                "id": f"exp_{exp_id:03d}",
                "name": f"Ablation: without {comp.get('name', 'component')}",
                "type": "ablation",
                "data_origin": "real",
                "parameters": {
                    "model": models[0] if models else "ProposedMethod",
                    "dataset": datasets[0] if datasets else "default_dataset",
                    "ablation": comp.get("name", "component"),
                    "metrics": metrics,
                },
                "expected_runtime": "TBD",
                "claims_addressed": [f"claim_{exp_id:03d}"],
            })
            exp_id += 1

        # Ensure at least one synthetic experiment.
        experiments.append({
            "id": f"exp_{exp_id:03d}",
            "name": "Synthetic validation",
            "type": "validation",
            "data_origin": "synthetic",
            "parameters": {
                "model": models[0] if models else "ProposedMethod",
                "dataset": "synthetic_data",
                "metrics": metrics,
            },
            "expected_runtime": "short",
            "claims_addressed": ["claim_synth"],
        })

        return {"experiments": experiments}

    def _build_claim_evidence_plan(
        self,
        experiment_content: str,
        experiment_matrix: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build claim_evidence_plan.json conforming to schema."""
        claims: List[Dict[str, Any]] = []
        experiments = experiment_matrix.get("experiments", [])

        # Extract expected results / claims from experiment content.
        expected_items = self._extract_section_items(experiment_content, "Expected")

        # Build claims from experiment types.
        seen_claims: set = set()
        for exp in experiments:
            claim_id = exp.get("claims_addressed", ["claim_001"])[0]
            if claim_id in seen_claims:
                continue
            seen_claims.add(claim_id)

            exp_type = exp.get("type", "main")
            if exp_type == "main":
                statement = f"The proposed method achieves competitive performance on {exp.get('parameters', {}).get('dataset', 'benchmark')}."
                evidence_type = "quantitative"
            elif exp_type == "baseline":
                statement = f"Baseline {exp.get('parameters', {}).get('model', '')} provides reference performance."
                evidence_type = "quantitative"
            elif exp_type == "ablation":
                statement = f"Removing {exp.get('parameters', {}).get('ablation', 'component')} degrades performance."
                evidence_type = "quantitative"
            else:
                statement = f"Validation experiment confirms method correctness."
                evidence_type = "qualitative"

            claims.append({
                "id": claim_id,
                "statement": statement,
                "evidence_type": evidence_type,
                "experiments": [exp["id"] for exp in experiments
                                if claim_id in exp.get("claims_addressed", [])],
                "pass_criteria": {
                    "metric": exp.get("parameters", {}).get("metrics", ["accuracy"]),
                    "threshold": "competitive with or better than baseline",
                },
            })

        # Add a claim from expected results if available.
        if expected_items:
            claims.append({
                "id": "claim_expected",
                "statement": expected_items[0],
                "evidence_type": "quantitative",
                "experiments": [e["id"] for e in experiments[:3]],
                "pass_criteria": {
                    "metric": "overall",
                    "threshold": "as specified in expected results",
                },
            })

        if not claims:
            claims.append({
                "id": "claim_001",
                "statement": "The proposed method is effective.",
                "evidence_type": "quantitative",
                "experiments": [e["id"] for e in experiments[:2]],
                "pass_criteria": {"metric": "accuracy", "threshold": "> baseline"},
            })

        return {"claims": claims}

    def _build_paper_figure_plan(
        self,
        experiment_content: str,
        experiment_matrix: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build paper_figure_plan.yaml conforming to schema."""
        experiments = experiment_matrix.get("experiments", [])
        main_exps = [e for e in experiments if e.get("type") == "main"]
        baseline_exps = [e for e in experiments if e.get("type") == "baseline"]
        ablation_exps = [e for e in experiments if e.get("type") == "ablation"]

        figures: List[Dict[str, Any]] = [
            {
                "id": "fig_1",
                "title": "Main Results Comparison",
                "type": "bar_chart",
                "data_source": "main_experiment_results",
                "experiments": [e["id"] for e in main_exps[:5]] +
                               [e["id"] for e in baseline_exps[:3]],
            },
            {
                "id": "fig_2",
                "title": "Ablation Study Results",
                "type": "bar_chart",
                "data_source": "ablation_experiment_results",
                "experiments": [e["id"] for e in ablation_exps[:5]],
            },
            {
                "id": "fig_3",
                "title": "Performance vs. Dataset Size",
                "type": "line_chart",
                "data_source": "scaling_experiment_results",
                "experiments": [e["id"] for e in main_exps[:3]],
            },
        ]

        tables: List[Dict[str, Any]] = [
            {
                "id": "tab_1",
                "title": "Main Results Table",
                "data_source": "main_experiment_results",
            },
            {
                "id": "tab_2",
                "title": "Ablation Results Table",
                "data_source": "ablation_experiment_results",
            },
            {
                "id": "tab_3",
                "title": "Dataset Statistics",
                "data_source": "dataset_info",
            },
        ]

        return {"figures": figures, "tables": tables}

    # ------------------------------------------------------------------
    # v8.3 builders
    # ------------------------------------------------------------------

    def _build_experiment_plan_yaml(
        self,
        task_id: str,
        method_spec: Dict[str, Any],
        experiment_matrix: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build structured experiment_plan.yaml conforming to v8.3 schema."""
        experiments_all = experiment_matrix.get("experiments", [])

        main_experiments: List[Dict[str, Any]] = []
        ablation_experiments: List[Dict[str, Any]] = []
        baseline_experiments: List[Dict[str, Any]] = []

        evaluation_metrics: List[str] = []

        for exp in experiments_all:
            exp_type = exp.get("type", "main")
            entry = {
                "id": exp.get("id", ""),
                "name": exp.get("name", ""),
                "type": exp_type,
                "dataset": exp.get("parameters", {}).get("dataset", ""),
                "parameters": exp.get("parameters", {}),
            }
            if exp_type == "ablation":
                ablation_experiments.append(entry)
            elif exp_type == "baseline":
                baseline_experiments.append(entry)
            else:
                main_experiments.append(entry)

            # Collect evaluation metrics from the first available experiment.
            if not evaluation_metrics:
                metrics = exp.get("parameters", {}).get("metrics", [])
                if metrics:
                    evaluation_metrics = list(metrics)

        if not evaluation_metrics:
            evaluation_metrics = ["accuracy"]

        return {
            "experiment_id": f"exp_plan_{task_id}",
            "method_name": method_spec.get("method_name", "Proposed Method"),
            "experiments": main_experiments,
            "ablation_experiments": ablation_experiments,
            "baseline_experiments": baseline_experiments,
            "evaluation_metrics": evaluation_metrics,
        }

    def _build_stage_report(
        self,
        task_id: str,
        method_spec: Dict[str, Any],
        experiment_matrix: Dict[str, Any],
        warnings: List[str],
        errors: List[str],
    ) -> str:
        """Build Stage_Report.md in Chinese conforming to v8.3 schema."""
        experiments_all = experiment_matrix.get("experiments", [])
        total_experiments = len(experiments_all)
        ablation_count = len(
            [e for e in experiments_all if e.get("type") == "ablation"]
        )
        baseline_count = len(
            [e for e in experiments_all if e.get("type") == "baseline"]
        )

        status = "完成" if not errors else "部分完成"

        lines = [
            "# Module 07 -- 实验规划 阶段报告",
            "",
            f"**任务 ID:** {task_id}",
            f"**时间戳:** {datetime.now().isoformat()}",
            f"**状态:** {status}",
            "",
            "## 当前目标",
            "",
            "设计实验矩阵、消融实验和基线对比方案。",
            "",
            "## 输入",
            "",
            "- method_spec.json",
            "- theory_analysis.md",
            "",
            "## 输出",
            "",
            "- experiment_plan.yaml",
            "- ablation_matrix.json",
            "- baseline_comparison.json",
            "- Stage_Report.md",
            "",
            "## 完成状态",
            "",
            f"- 实验数量: {total_experiments}",
            f"- 消融数量: {ablation_count}",
            f"- 基线数量: {baseline_count}",
        ]

        if warnings:
            lines.extend(["", "## 警告", ""])
            for w in warnings:
                lines.append(f"- {w}")

        if errors:
            lines.extend(["", "## 错误", ""])
            for e in errors:
                lines.append(f"- {e}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Text extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_section_items(
        content: str, section_keyword: str
    ) -> List[str]:
        """Extract bullet/numbered items from a markdown section."""
        items: List[str] = []
        # Find section headers matching the keyword.
        pattern = re.compile(
            rf"##\s*.*{section_keyword}.*\n(.+?)(?=\n##|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(content):
            section_text = match.group(1)
            # Extract list items.
            for line in section_text.split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    items.append(line[2:].strip())
                elif re.match(r"^\d+[.:]\s", line):
                    items.append(re.sub(r"^\d+[.:]\s*", "", line).strip())
                elif line and not line.startswith("#"):
                    items.append(line)
        return [item for item in items if item]

    @staticmethod
    def _dict_to_yaml(data: Any, indent: int = 0) -> str:
        """Simple YAML serialiser for flat/nested dicts and lists."""
        lines: List[str] = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(ExperimentPlanningModule._dict_to_yaml(value, indent + 1))
                elif isinstance(value, str):
                    # Escape strings that look like YAML special values.
                    if value.startswith(("-", "*", "&", "!", "{", "[", "?", "|", ">", "@", "`")):
                        lines.append(f'{prefix}{key}: "{value}"')
                    else:
                        lines.append(f"{prefix}{key}: {value}")
                elif isinstance(value, bool):
                    lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
                elif value is None:
                    lines.append(f"{prefix}{key}: null")
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    lines.append(f"{prefix}-")
                    lines.append(ExperimentPlanningModule._dict_to_yaml(item, indent + 1))
                elif isinstance(item, str):
                    lines.append(f"{prefix}- {item}")
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)
