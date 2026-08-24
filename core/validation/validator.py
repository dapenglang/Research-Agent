"""Base validators for module inputs, outputs, and quality assessment.

Provides three classes:

- :class:`InputValidator`  — checks that required input files exist and match
  their expected schema.
- :class:`OutputValidator` — checks that expected output files exist and are
  non-empty.
- :class:`QualityAssessor` — evaluates quality metrics against hard
  requirements (must pass) and soft thresholds (warn if below).

All methods return :class:`ValidationResult` objects with a
:class:`~core.contracts.module_contract.ModuleStatus`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from Research_Agent_v3.core.contracts.module_contract import ModuleStatus


@dataclass
class ValidationIssue:
    """A single validation problem."""

    severity: str  # "error" or "warning"
    field: str
    message: str


@dataclass
class ValidationResult:
    """Structured result of a validation or quality assessment."""

    status: ModuleStatus = ModuleStatus.PASS
    score: float = 1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    checked_fields: List[str] = field(default_factory=list)

    def add_error(self, field_name: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", field_name, message))
        self.status = ModuleStatus.FAIL

    def add_warning(self, field_name: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", field_name, message))
        if self.status != ModuleStatus.FAIL:
            self.status = ModuleStatus.WARNING

    @property
    def passed(self) -> bool:
        return self.status == ModuleStatus.PASS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "issues": [
                {"severity": i.severity, "field": i.field, "message": i.message}
                for i in self.issues
            ],
            "checked_fields": self.checked_fields,
        }


class InputValidator:
    """Validate module input files and fields against a schema.

    The *schema* is a dict mapping field names to dicts with optional keys:
    ``required`` (bool), ``type`` (str), ``file_exists`` (bool).
    """

    def __init__(self, schema: Dict[str, Dict[str, Any]]) -> None:
        self.schema = schema

    def validate(self, inputs: Dict[str, Any]) -> ValidationResult:
        """Validate *inputs* against the schema.

        Args:
            inputs: Mapping of field names to values (file paths or data).

        Returns:
            A :class:`ValidationResult` with PASS/WARNING/FAIL status.
        """
        result = ValidationResult()

        for field_name, spec in self.schema.items():
            result.checked_fields.append(field_name)
            required = spec.get("required", True)

            if field_name not in inputs or inputs[field_name] is None:
                if required:
                    result.add_error(field_name, f"Required input '{field_name}' is missing")
                continue

            value = inputs[field_name]

            # Check file existence if specified
            if spec.get("file_exists") and isinstance(value, (str, Path)):
                if not Path(value).exists():
                    result.add_error(field_name, f"Input file does not exist: {value}")
                elif Path(value).stat().st_size == 0:
                    result.add_warning(field_name, f"Input file is empty: {value}")

            # Type checking
            expected_type = spec.get("type")
            if expected_type:
                type_map = {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                }
                expected_py = type_map.get(expected_type)
                if expected_py and not isinstance(value, expected_py):
                    result.add_error(
                        field_name,
                        f"Input '{field_name}' expected type {expected_type}, "
                        f"got {type(value).__name__}",
                    )

        return result


class OutputValidator:
    """Validate module output files and fields against a schema.

    Similar to :class:`InputValidator` but also checks that output files are
    non-empty and optionally valid JSON/YAML.
    """

    def __init__(self, schema: Dict[str, Dict[str, Any]]) -> None:
        self.schema = schema

    def validate(self, outputs: Dict[str, Any]) -> ValidationResult:
        """Validate *outputs* against the schema.

        Args:
            outputs: Mapping of field names to output file paths or values.

        Returns:
            A :class:`ValidationResult`.
        """
        result = ValidationResult()

        for field_name, spec in self.schema.items():
            result.checked_fields.append(field_name)
            required = spec.get("required", True)

            if field_name not in outputs or outputs[field_name] is None:
                if required:
                    result.add_error(field_name, f"Required output '{field_name}' is missing")
                continue

            value = outputs[field_name]

            if spec.get("file_exists") and isinstance(value, (str, Path)):
                p = Path(value)
                if not p.exists():
                    result.add_error(field_name, f"Output file does not exist: {value}")
                elif p.stat().st_size == 0:
                    result.add_error(field_name, f"Output file is empty: {value}")
                else:
                    # Optionally validate JSON
                    if spec.get("valid_json") and p.suffix in (".json",):
                        try:
                            json.loads(p.read_text(encoding="utf-8"))
                        except json.JSONDecodeError as exc:
                            result.add_error(
                                field_name,
                                f"Output file is not valid JSON: {exc}",
                            )

        return result


class QualityAssessor:
    """Evaluate quality metrics against hard requirements and soft thresholds.

    Hard requirements: if any fail, overall status is ``FAIL``.
    Soft thresholds: if below threshold but above minimum, status is ``WARNING``.
    """

    def __init__(
        self,
        hard_requirements: Optional[Dict[str, float]] = None,
        soft_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        """
        Args:
            hard_requirements: Mapping of metric name to minimum acceptable value.
                If a metric falls below this, it is a FAIL.
            soft_thresholds: Mapping of metric name to ``{"warning": float,
                "target": float}``.  Below *warning* is WARNING, below
                *target* is also WARNING (but above *warning* from the
                hard requirement).
        """
        self.hard_requirements = hard_requirements or {}
        self.soft_thresholds = soft_thresholds or {}

    def assess(self, metrics: Dict[str, float]) -> ValidationResult:
        """Assess quality metrics.

        Args:
            metrics: Mapping of metric name to measured value.

        Returns:
            A :class:`ValidationResult` with status and score.
        """
        result = ValidationResult()
        total_score = 0.0
        score_count = 0

        # Check hard requirements
        for metric_name, min_value in self.hard_requirements.items():
            result.checked_fields.append(metric_name)
            actual = metrics.get(metric_name)
            if actual is None:
                result.add_error(metric_name, f"Required metric '{metric_name}' not provided")
                continue
            if actual < min_value:
                result.add_error(
                    metric_name,
                    f"Hard requirement failed: {metric_name}={actual} < {min_value}",
                )
            else:
                total_score += 1.0
                score_count += 1

        # Check soft thresholds
        for metric_name, thresholds in self.soft_thresholds.items():
            result.checked_fields.append(metric_name)
            warning_level = thresholds.get("warning", 0.0)
            target_level = thresholds.get("target", warning_level)

            actual = metrics.get(metric_name)
            if actual is None:
                result.add_warning(metric_name, f"Metric '{metric_name}' not provided")
                continue

            if actual < warning_level:
                result.add_warning(
                    metric_name,
                    f"Below warning threshold: {metric_name}={actual} < {warning_level}",
                )
                # Partial credit proportional to how close to warning level
                if warning_level > 0:
                    total_score += max(0.0, actual / warning_level)
                else:
                    total_score += 0.0
                score_count += 1
            elif actual < target_level:
                result.add_warning(
                    metric_name,
                    f"Below target: {metric_name}={actual} < {target_level}",
                )
                if target_level > 0:
                    total_score += 0.5 + 0.5 * (actual - warning_level) / max(
                        target_level - warning_level, 1e-9
                    )
                else:
                    total_score += 0.5
                score_count += 1
            else:
                total_score += 1.0
                score_count += 1

        # Compute overall score
        result.score = total_score / score_count if score_count > 0 else 1.0
        # Adjust score if there are errors
        if result.status == ModuleStatus.FAIL:
            result.score = min(result.score, 0.49)

        return result
