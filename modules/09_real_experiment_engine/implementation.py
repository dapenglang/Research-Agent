"""
Module 09 — Real Experiment Engine

GENERIC real experiment engine. NOT bound to SAMRA or any specific method.
Loads method backend from adapter registry based on research_task.yaml.

Supports GPU long-running experiment recovery via state machine integration:
- EXPERIMENT_RUNNING → checkpoint created
- EXPERIMENT_INTERRUPTED → checkpoint available for resume
- EXPERIMENT_RESUMING → loads checkpoint and continues

SAMRA's runtime components are legacy/example backends registered via
adapters/samra_adapter.py. New research methods register their own adapters.

v8.3 additions:
  - Stage_Report.md for pipeline tracking
  - Raw/processed data saving with proper paths
"""

import sys
import os
import json
import time
import uuid
from typing import Any, Dict, List, Optional

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from interface import RealExperimentInput, RealExperimentOutput, Module09Interface
import adapters  # triggers SAMRA registration via __init__.py
from Research_Agent_v3.adapters.method_backend_interface import backend_registry, ExperimentResult


class RealExperimentEngine(Module09Interface):
    """Generic real experiment engine with checkpoint support."""

    MODULE_ID = "09"
    MODULE_NAME = "Real Experiment Engine"

    def load_config(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._method_name = config.get("experiment", {}).get("method", "default")
        self._seed = config.get("experiment", {}).get("real", {}).get("seed", 42)
        self._checkpoint_dir = config.get("experiment", {}).get("real", {}).get(
            "checkpoint_dir", "experiments/checkpoints"
        )
        self._resume_from_checkpoint = config.get("experiment", {}).get("real", {}).get(
            "resume_from_checkpoint", False
        )
        self._checkpoint_interval = config.get("experiment", {}).get("real", {}).get(
            "checkpoint_interval", 100
        )

    def validate_input(self, input_data: RealExperimentInput) -> bool:
        required = ["method_spec.json", "experiment_matrix.yaml", "claim_evidence_plan.json"]
        for f in required:
            if f not in input_data.input_files:
                return False
        return True

    def execute(self, input_data: RealExperimentInput) -> RealExperimentOutput:
        backend = backend_registry.get(self._method_name.lower())

        with open(input_data.input_files.get("method_spec.json", ""), "r") as f:
            method_spec = json.load(f)
        spec = backend.load_spec(method_spec)

        experiment_config = self._config.get("experiment", {}).get("real", {})
        experiment_config["task_id"] = input_data.task_id

        model_handler = self._load_model_handler(experiment_config)

        if self._resume_from_checkpoint:
            checkpoint = self._load_checkpoint(input_data.task_id)
            if checkpoint:
                experiment_config["checkpoint"] = checkpoint
                experiment_config["resume"] = True

        try:
            result = backend.run_real_experiment(
                spec=spec,
                experiment_config=experiment_config,
                model_handler=model_handler,
                seed=self._seed,
            )
        except NotImplementedError as e:
            return RealExperimentOutput(
                task_id=input_data.task_id,
                output_files={},
                manifest={
                    "module_id": self.MODULE_ID,
                    "status": "FAIL",
                    "error": f"Backend '{backend.backend_name}' does not support real experiments: {e}",
                    "data_origin": "real",
                    "method_backend": backend.backend_name,
                },
                warnings=[],
                errors=[str(e)],
            )

        self._save_checkpoint(input_data.task_id, result)

        # v8.3: Save raw and processed results with proper paths
        exp_output_dir = os.path.join("experiments", input_data.task_id)
        raw_dir = os.path.join(exp_output_dir, "raw_results")
        processed_dir = os.path.join(exp_output_dir, "processed_results")
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        raw_metrics_path = os.path.join(raw_dir, "metrics.json")
        with open(raw_metrics_path, "w") as f:
            json.dump(result.metrics or {}, f, indent=2)

        summary_path = os.path.join(processed_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump({
                "experiment_id": result.experiment_id,
                "seed": result.seed,
                "data_origin": result.data_origin,
                "metrics_summary": {k: v for k, v in (result.metrics or {}).items()},
            }, f, indent=2)

        # v8.3: Stage_Report.md
        stage_report = self._build_stage_report(
            input_data.task_id, result, backend.backend_name
        )
        stage_path = os.path.join(exp_output_dir, "Stage_Report.md")
        with open(stage_path, "w", encoding="utf-8") as f:
            f.write(stage_report)

        return RealExperimentOutput(
            task_id=input_data.task_id,
            output_files={
                f"experiments/{input_data.task_id}/raw_results/metrics.json": raw_metrics_path,
                f"experiments/{input_data.task_id}/processed_results/summary.json": summary_path,
                f"experiments/{input_data.task_id}/Stage_Report.md": stage_path,
            },
            manifest={
                "module_id": self.MODULE_ID,
                "status": "PASS" if result.metrics else "FAIL",
                "data_origin": "real",
                "method_backend": backend.backend_name,
                "experiment_id": result.experiment_id,
                "seed": result.seed,
                "timestamp": time.time(),
            },
            warnings=[],
            errors=[result.raw_data.get("error", "")] if isinstance(result.raw_data, dict) and "error" in result.raw_data else [],
        )

    def _load_model_handler(self, config: Dict[str, Any]) -> Any:
        """Load model handler based on config. Returns None if not available."""
        model_path = config.get("model_path")
        if model_path and os.path.exists(model_path):
            try:
                import torch
                return torch.load(model_path)
            except ImportError:
                return None
        return None

    def _save_checkpoint(self, task_id: str, result: ExperimentResult) -> None:
        """Save experiment checkpoint for GPU recovery."""
        checkpoint_path = os.path.join(self._checkpoint_dir, task_id, "checkpoint.json")
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w") as f:
            json.dump({
                "experiment_id": result.experiment_id,
                "seed": result.seed,
                "data_origin": result.data_origin,
                "metrics": result.metrics,
                "timestamp": time.time(),
            }, f, indent=2)

    def _load_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint for experiment resume."""
        checkpoint_path = os.path.join(self._checkpoint_dir, task_id, "checkpoint.json")
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, "r") as f:
                return json.load(f)
        return None

    def validate_output(self, output: RealExperimentOutput) -> bool:
        return output.manifest.get("status") in ("PASS", "WARNING")

    def quality_assessment(self, output: RealExperimentOutput) -> Dict[str, Any]:
        return {
            "hard_requirements": {
                "data_origin_real": output.manifest.get("data_origin") == "real",
                "metrics_present": bool(output.manifest.get("status") == "PASS"),
                "no_errors": len(output.errors) == 0,
            },
            "soft_thresholds": {
                "backend_specified": bool(output.manifest.get("method_backend")),
            },
        }

    def write_manifest(self, output: RealExperimentOutput) -> Dict[str, Any]:
        return output.manifest

    def write_report(self, output: RealExperimentOutput) -> str:
        return (
            f"# Module 09 — Real Experiment Engine Report\n\n"
            f"- **Task ID**: {output.task_id}\n"
            f"- **Status**: {output.manifest.get('status')}\n"
            f"- **Backend**: {output.manifest.get('method_backend')}\n"
            f"- **Data Origin**: {output.manifest.get('data_origin')}\n"
            f"- **Experiment ID**: {output.manifest.get('experiment_id')}\n"
            f"- **Errors**: {len(output.errors)}\n"
            f"- **Warnings**: {len(output.warnings)}\n"
        )

    def _build_stage_report(self, task_id: str, result: Any, backend_name: str) -> str:
        """v8.3: Build Stage_Report.md for Module 09."""
        from datetime import datetime
        status = "PASS" if result.metrics else "FAIL"
        metrics = result.metrics or {}

        lines = [
            "# Module 09 — Real Experiment Engine Stage Report",
            "",
            f"**Task ID:** {task_id}",
            f"**Timestamp:** {datetime.now().isoformat()}",
            f"**Status:** {status}",
            "",
            "## 当前目标",
            "",
            "在真实GPU环境中运行实验，保存原始数据和处理后数据。",
            "",
            "## 输入",
            "",
            "- method_spec.json (方法规范)",
            "- experiment_matrix.yaml (实验矩阵)",
            "- claim_evidence_plan.json (Claim-Evidence计划)",
            "",
            "## 输出",
            "",
            f"- raw_results/metrics.json (原始指标)",
            f"- processed_results/summary.json (处理后摘要)",
            f"- Stage_Report.md (阶段报告)",
            "",
            "## 完成状态",
            "",
            f"- 实验ID: {result.experiment_id}",
            f"- 后端: {backend_name}",
            f"- 种子: {result.seed}",
            f"- 数据来源: {result.data_origin}",
            f"- 指标数量: {len(metrics)}",
            "",
        ]

        if metrics:
            lines.extend(["## 指标概览", ""])
            for k, v in list(metrics.items())[:10]:
                lines.append(f"- {k}: {v}")

        return "\n".join(lines)
