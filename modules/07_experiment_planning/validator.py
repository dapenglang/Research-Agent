"""
Module 07 — Experiment Planning
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import ExperimentPlanningInput, ExperimentPlanningOutput


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        is_valid: True if all hard requirements pass.
        errors: List of hard requirement violations (must be fixed).
        warnings: List of soft threshold warnings (should be reviewed).
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add a hard error and mark result as invalid."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a soft warning (does not affect is_valid)."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another ValidationResult into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if other.errors:
            self.is_valid = False


class InputValidator:
    """Validator for Module 07 — Experiment Planning inputs.

    Input validation rules:
    - method_spec.json exists and is valid JSON
    - method_spec has components and schemas
    """

    REQUIRED_FILES = ['method_spec.json']
    OPTIONAL_FILES = []

    def validate(self, input_data: Any) -> ValidationResult:
        """Validate module input against required files and schemas.

        Args:
            input_data: Module input (expected to have input_files dict).

        Returns:
            ValidationResult with is_valid, errors, and warnings.
        """
        result = ValidationResult()

        # Check required input files exist
        input_files = getattr(input_data, "input_files", {})
        if "method_spec.json" not in input_files:
            result.add_error("Missing required input file: method_spec.json")

        # Check input file contents (schema-level validation)
        for filename, filepath in input_files.items():
            file_errors = self._validate_file(filename, filepath)
            result.errors.extend(file_errors)

        if result.errors:
            result.is_valid = False

        return result

    def _validate_file(self, filename: str, filepath: str) -> List[str]:
        """Validate a single input file against its schema.

        Args:
            filename: Name of the input file.
            filepath: Path to the input file.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: List[str] = []
        # TODO: Implement schema-level validation using schemas from schema.py
        # from .schema import get_input_schema
        # schema = get_input_schema(filename)
        # if schema:
        #     ... validate file contents against schema ...
        return errors


class OutputValidator:
    """Validator for Module 07 — Experiment Planning outputs.

    Output validation rules:
    - Every experiment in matrix has unique id
    - Every claim has at least 1 experiment mapping
    - paper_figure_plan experiments reference valid experiment ids

    Hard requirements (must pass):
    - experiment_matrix.yaml has at least 1 experiment
    - claim_evidence_plan.json has at least 1 claim with pass_criteria
    - paper_figure_plan.yaml has at least 1 figure
    - Every experiment maps to at least 1 claim

    Soft thresholds (warnings):
    - Prefer >= 3 experiments for robust evaluation
    - Prefer >= 2 figure types (e.g., line chart, bar chart, table)
    """

    REQUIRED_FILES = ['experiment_plan.md', 'experiment_matrix.yaml', 'claim_evidence_plan.json', 'paper_figure_plan.yaml']

    def validate(self, output: Any) -> ValidationResult:
        """Validate module output against required files and schemas.

        Args:
            output: Module output (expected to have output_files dict).

        Returns:
            ValidationResult with is_valid, errors, and warnings.
        """
        result = ValidationResult()

        # Check required output files exist
        output_files = getattr(output, "output_files", {})
        if "experiment_plan.md" not in output_files:
            result.add_error("Missing required output file: experiment_plan.md")
        if "experiment_matrix.yaml" not in output_files:
            result.add_error("Missing required output file: experiment_matrix.yaml")
        if "claim_evidence_plan.json" not in output_files:
            result.add_error("Missing required output file: claim_evidence_plan.json")
        if "paper_figure_plan.yaml" not in output_files:
            result.add_error("Missing required output file: paper_figure_plan.yaml")

        # Check output file contents (schema-level validation)
        for filename, filepath in output_files.items():
            file_errors = self._validate_file(filename, filepath)
            result.errors.extend(file_errors)

        # Run hard requirement checks
        result.merge(self._check_hard_requirement_0(output))
        result.merge(self._check_hard_requirement_1(output))
        result.merge(self._check_hard_requirement_2(output))
        result.merge(self._check_hard_requirement_3(output))

        # Run soft threshold checks
        thresh_result = self._check_soft_threshold_0(output)
        result.warnings.extend(thresh_result)
        thresh_result = self._check_soft_threshold_1(output)
        result.warnings.extend(thresh_result)

        if result.errors:
            result.is_valid = False

        return result

    def _check_hard_requirement_0(self, output: ExperimentPlanningOutput) -> List[str]:
        """Hard requirement: experiment_matrix.yaml has at least 1 experiment"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: experiment_matrix.yaml has at least 1 experiment
        return errors
    def _check_hard_requirement_1(self, output: ExperimentPlanningOutput) -> List[str]:
        """Hard requirement: claim_evidence_plan.json has at least 1 claim with pass_criteria"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: claim_evidence_plan.json has at least 1 claim with pass_criteria
        return errors
    def _check_hard_requirement_2(self, output: ExperimentPlanningOutput) -> List[str]:
        """Hard requirement: paper_figure_plan.yaml has at least 1 figure"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: paper_figure_plan.yaml has at least 1 figure
        return errors
    def _check_hard_requirement_3(self, output: ExperimentPlanningOutput) -> List[str]:
        """Hard requirement: Every experiment maps to at least 1 claim"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Every experiment maps to at least 1 claim
        return errors

    def _check_soft_threshold_0(self, output: ExperimentPlanningOutput) -> List[str]:
        """Soft threshold: Prefer >= 3 experiments for robust evaluation"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 3 experiments for robust evaluation
        return warnings
    def _check_soft_threshold_1(self, output: ExperimentPlanningOutput) -> List[str]:
        """Soft threshold: Prefer >= 2 figure types (e.g., line chart, bar chart, table)"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 2 figure types (e.g., line chart, bar chart, table)
        return warnings

    def _validate_file(self, filename: str, filepath: str) -> List[str]:
        """Validate a single output file against its schema.

        Args:
            filename: Name of the output file.
            filepath: Path to the output file.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: List[str] = []
        # TODO: Implement schema-level validation using schemas from schema.py
        # from .schema import get_output_schema
        # schema = get_output_schema(filename)
        # if schema:
        #     ... validate file contents against schema ...
        return errors
