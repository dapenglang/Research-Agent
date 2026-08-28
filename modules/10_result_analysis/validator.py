"""
Module 10 — Scientific Result Analysis
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import ResultAnalysisInput, ResultAnalysisOutput


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
    """Validator for Module 10 — Scientific Result Analysis inputs.

    Input validation rules:
    - synthetic_results/ exists with metrics.csv and statistics.json
    - claim_evidence_plan.json exists with claims
    - If real experiments exist, they have processed_results
    """

    REQUIRED_FILES = ['synthetic_results/', 'claim_evidence_plan.json']
    OPTIONAL_FILES = ['experiments/<task_id>/']

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
        if "synthetic_results/" not in input_files:
            result.add_error("Missing required input file: synthetic_results/")
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
    """Validator for Module 10 — Scientific Result Analysis outputs.

    Output validation rules:
    - decision.json decision is one of the 6 allowed values
    - All claims from plan are addressed in claim_evidence_mapping
    - decision is consistent with claim verdicts

    Hard requirements (must pass):
    - decision.json has a valid decision value
    - Every claim in claim_evidence_plan has a verdict
    - scientific_result_analysis.md is non-empty

    Soft thresholds (warnings):
    - Prefer >= 80% of claims have definitive verdict (pass/fail)
    - Prefer revision_recommendation.md with actionable items
    """

    REQUIRED_FILES = ['scientific_result_analysis.md', 'claim_evidence_mapping.md', 'revision_recommendation.md', 'decision.json']

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
        if "scientific_result_analysis.md" not in output_files:
            result.add_error("Missing required output file: scientific_result_analysis.md")
        if "claim_evidence_mapping.md" not in output_files:
            result.add_error("Missing required output file: claim_evidence_mapping.md")
        if "revision_recommendation.md" not in output_files:
            result.add_error("Missing required output file: revision_recommendation.md")
        if "decision.json" not in output_files:
            result.add_error("Missing required output file: decision.json")

        # Check output file contents (schema-level validation)
        for filename, filepath in output_files.items():
            file_errors = self._validate_file(filename, filepath)
            result.errors.extend(file_errors)

        # Run hard requirement checks
        result.merge(self._check_hard_requirement_0(output))
        result.merge(self._check_hard_requirement_1(output))
        result.merge(self._check_hard_requirement_2(output))

        # Run soft threshold checks
        thresh_result = self._check_soft_threshold_0(output)
        result.warnings.extend(thresh_result)
        thresh_result = self._check_soft_threshold_1(output)
        result.warnings.extend(thresh_result)

        if result.errors:
            result.is_valid = False

        return result

    def _check_hard_requirement_0(self, output: ResultAnalysisOutput) -> List[str]:
        """Hard requirement: decision.json has a valid decision value"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: decision.json has a valid decision value
        return errors
    def _check_hard_requirement_1(self, output: ResultAnalysisOutput) -> List[str]:
        """Hard requirement: Every claim in claim_evidence_plan has a verdict"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Every claim in claim_evidence_plan has a verdict
        return errors
    def _check_hard_requirement_2(self, output: ResultAnalysisOutput) -> List[str]:
        """Hard requirement: scientific_result_analysis.md is non-empty"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: scientific_result_analysis.md is non-empty
        return errors

    def _check_soft_threshold_0(self, output: ResultAnalysisOutput) -> List[str]:
        """Soft threshold: Prefer >= 80% of claims have definitive verdict (pass/fail)"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 80% of claims have definitive verdict (pass/fail)
        return warnings
    def _check_soft_threshold_1(self, output: ResultAnalysisOutput) -> List[str]:
        """Soft threshold: Prefer revision_recommendation.md with actionable items"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer revision_recommendation.md with actionable items
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
