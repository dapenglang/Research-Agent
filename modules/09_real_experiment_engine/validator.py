"""
Module 09 — Real Experiment Engine
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import RealExperimentInput, RealExperimentOutput


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
    """Validator for Module 09 — Real Experiment Engine inputs.

    Input validation rules:
    - method_spec.json exists and is valid
    - experiment_matrix.yaml exists with real experiments
    - claim_evidence_plan.json exists
    - Only experiments with data_origin='real' are processed
    """

    REQUIRED_FILES = ['method_spec.json', 'experiment_matrix.yaml', 'claim_evidence_plan.json']
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
        if "experiment_matrix.yaml" not in input_files:
            result.add_error("Missing required input file: experiment_matrix.yaml")
        if "claim_evidence_plan.json" not in input_files:
            result.add_error("Missing required input file: claim_evidence_plan.json")

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
    """Validator for Module 09 — Real Experiment Engine outputs.

    Output validation rules:
    - raw_results have data_origin='real'
    - processed_results have data_origin='real'
    - provenance has data_origin='real'
    - environment/ has requirements.txt
    - All real experiments from matrix are represented

    Hard requirements (must pass):
    - All output files MUST have data_origin='real'
    - config/ and raw_results/ directories exist for each experiment
    - provenance/ records adapter_used and environment
    - SAMRA is an adapter/plugin, NOT built into this module

    Soft thresholds (warnings):
    - Prefer checkpoints/ saved for reproducibility
    - Prefer git_commit recorded in provenance
    """

    REQUIRED_FILES = ['experiments/<task_id>/config/', 'experiments/<task_id>/code/', 'experiments/<task_id>/checkpoints/', 'experiments/<task_id>/raw_results/', 'experiments/<task_id>/processed_results/', 'experiments/<task_id>/logs/', 'experiments/<task_id>/environment/', 'experiments/<task_id>/provenance/']

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
        if "experiments/<task_id>/config/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/config/")
        if "experiments/<task_id>/code/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/code/")
        if "experiments/<task_id>/checkpoints/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/checkpoints/")
        if "experiments/<task_id>/raw_results/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/raw_results/")
        if "experiments/<task_id>/processed_results/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/processed_results/")
        if "experiments/<task_id>/logs/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/logs/")
        if "experiments/<task_id>/environment/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/environment/")
        if "experiments/<task_id>/provenance/" not in output_files:
            result.add_error("Missing required output file: experiments/<task_id>/provenance/")

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

    def _check_hard_requirement_0(self, output: RealExperimentOutput) -> List[str]:
        """Hard requirement: All output files MUST have data_origin='real'"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: All output files MUST have data_origin='real'
        return errors
    def _check_hard_requirement_1(self, output: RealExperimentOutput) -> List[str]:
        """Hard requirement: config/ and raw_results/ directories exist for each experiment"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: config/ and raw_results/ directories exist for each experiment
        return errors
    def _check_hard_requirement_2(self, output: RealExperimentOutput) -> List[str]:
        """Hard requirement: provenance/ records adapter_used and environment"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: provenance/ records adapter_used and environment
        return errors
    def _check_hard_requirement_3(self, output: RealExperimentOutput) -> List[str]:
        """Hard requirement: SAMRA is an adapter/plugin, NOT built into this module"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: SAMRA is an adapter/plugin, NOT built into this module
        return errors

    def _check_soft_threshold_0(self, output: RealExperimentOutput) -> List[str]:
        """Soft threshold: Prefer checkpoints/ saved for reproducibility"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer checkpoints/ saved for reproducibility
        return warnings
    def _check_soft_threshold_1(self, output: RealExperimentOutput) -> List[str]:
        """Soft threshold: Prefer git_commit recorded in provenance"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer git_commit recorded in provenance
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
