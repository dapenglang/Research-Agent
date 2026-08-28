"""
Module 08 — Synthetic Experiment Engine
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import SyntheticExperimentInput, SyntheticExperimentOutput


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
    """Validator for Module 08 — Synthetic Experiment Engine inputs.

    Input validation rules:
    - method_spec.json exists and is valid
    - experiment_matrix.yaml exists with synthetic experiments
    - claim_evidence_plan.json exists
    - Only experiments with data_origin='synthetic' are processed
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
    """Validator for Module 08 — Synthetic Experiment Engine outputs.

    Output validation rules:
    - metrics.csv has data_origin column with all values='synthetic'
    - statistics.json has data_origin='synthetic'
    - provenance.json has data_origin='synthetic'
    - All experiments from matrix are represented in results

    Hard requirements (must pass):
    - All output files MUST have data_origin='synthetic'
    - metrics.csv exists with at least 1 row per experiment
    - provenance.json records adapter_used and adapter_version
    - Backend adapters (e.g., SAMRA) are plugins, NOT hardcoded

    Soft thresholds (warnings):
    - Prefer confidence intervals in statistics.json
    - Prefer raw results preserved for reproducibility
    """

    REQUIRED_FILES = ['synthetic_results/raw/', 'synthetic_results/processed/', 'synthetic_results/metrics.csv', 'synthetic_results/statistics.json', 'synthetic_results/figures/', 'synthetic_results/tables/', 'synthetic_results/analysis/', 'synthetic_results/provenance.json']

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
        if "synthetic_results/raw/" not in output_files:
            result.add_error("Missing required output file: synthetic_results/raw/")
        if "synthetic_results/processed/" not in output_files:
            result.add_error("Missing required output file: synthetic_results/processed/")
        if "synthetic_results/metrics.csv" not in output_files:
            result.add_error("Missing required output file: synthetic_results/metrics.csv")
        if "synthetic_results/statistics.json" not in output_files:
            result.add_error("Missing required output file: synthetic_results/statistics.json")
        if "synthetic_results/figures/" not in output_files:
            result.add_error("Missing required output file: synthetic_results/figures/")
        if "synthetic_results/tables/" not in output_files:
            result.add_error("Missing required output file: synthetic_results/tables/")
        if "synthetic_results/analysis/" not in output_files:
            result.add_error("Missing required output file: synthetic_results/analysis/")
        if "synthetic_results/provenance.json" not in output_files:
            result.add_error("Missing required output file: synthetic_results/provenance.json")

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

    def _check_hard_requirement_0(self, output: SyntheticExperimentOutput) -> List[str]:
        """Hard requirement: All output files MUST have data_origin='synthetic'"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: All output files MUST have data_origin='synthetic'
        return errors
    def _check_hard_requirement_1(self, output: SyntheticExperimentOutput) -> List[str]:
        """Hard requirement: metrics.csv exists with at least 1 row per experiment"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: metrics.csv exists with at least 1 row per experiment
        return errors
    def _check_hard_requirement_2(self, output: SyntheticExperimentOutput) -> List[str]:
        """Hard requirement: provenance.json records adapter_used and adapter_version"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: provenance.json records adapter_used and adapter_version
        return errors
    def _check_hard_requirement_3(self, output: SyntheticExperimentOutput) -> List[str]:
        """Hard requirement: Backend adapters (e.g., SAMRA) are plugins, NOT hardcoded"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Backend adapters (e.g., SAMRA) are plugins, NOT hardcoded
        return errors

    def _check_soft_threshold_0(self, output: SyntheticExperimentOutput) -> List[str]:
        """Soft threshold: Prefer confidence intervals in statistics.json"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer confidence intervals in statistics.json
        return warnings
    def _check_soft_threshold_1(self, output: SyntheticExperimentOutput) -> List[str]:
        """Soft threshold: Prefer raw results preserved for reproducibility"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer raw results preserved for reproducibility
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
