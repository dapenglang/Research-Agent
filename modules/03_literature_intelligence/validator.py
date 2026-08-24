"""
Module 03 — Literature Intelligence
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import LiteratureIntelligenceInput, LiteratureIntelligenceOutput


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
    """Validator for Module 03 — Literature Intelligence inputs.

    Input validation rules:
    - At least 1 normalized paper.md exists
    - Each paper.md is non-empty
    """

    REQUIRED_FILES = ['papers/<paper_id>/normalized/paper.md']
    OPTIONAL_FILES = ['papers/<paper_id>/equations.json', 'papers/<paper_id>/figures.json', 'papers/<paper_id>/tables.json']

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
        if "papers/<paper_id>/normalized/paper.md" not in input_files:
            result.add_error("Missing required input file: papers/<paper_id>/normalized/paper.md")

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
    """Validator for Module 03 — Literature Intelligence outputs.

    Output validation rules:
    - paper_analysis.json has required fields (paper_id, main_contribution, methodology)
    - literature_analysis_index.jsonl line count matches number of analyzed papers
    - No duplicate paper_ids in index

    Hard requirements (must pass):
    - paper_analysis.json exists for every normalized paper
    - Each analysis has main_contribution and methodology
    - literature_analysis_index.jsonl is valid JSONL

    Soft thresholds (warnings):
    - Prefer >= 90% of papers have limitations extracted
    - Prefer cross-paper relationship coverage >= 70%
    """

    REQUIRED_FILES = ['paper_analysis.json', 'paper_analysis.md', 'literature_analysis_index.jsonl', 'Module03_Validation_Report.md']

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
        if "paper_analysis.json" not in output_files:
            result.add_error("Missing required output file: paper_analysis.json")
        if "paper_analysis.md" not in output_files:
            result.add_error("Missing required output file: paper_analysis.md")
        if "literature_analysis_index.jsonl" not in output_files:
            result.add_error("Missing required output file: literature_analysis_index.jsonl")
        if "Module03_Validation_Report.md" not in output_files:
            result.add_error("Missing required output file: Module03_Validation_Report.md")

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

    def _check_hard_requirement_0(self, output: LiteratureIntelligenceOutput) -> List[str]:
        """Hard requirement: paper_analysis.json exists for every normalized paper"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: paper_analysis.json exists for every normalized paper
        return errors
    def _check_hard_requirement_1(self, output: LiteratureIntelligenceOutput) -> List[str]:
        """Hard requirement: Each analysis has main_contribution and methodology"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Each analysis has main_contribution and methodology
        return errors
    def _check_hard_requirement_2(self, output: LiteratureIntelligenceOutput) -> List[str]:
        """Hard requirement: literature_analysis_index.jsonl is valid JSONL"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: literature_analysis_index.jsonl is valid JSONL
        return errors

    def _check_soft_threshold_0(self, output: LiteratureIntelligenceOutput) -> List[str]:
        """Soft threshold: Prefer >= 90% of papers have limitations extracted"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 90% of papers have limitations extracted
        return warnings
    def _check_soft_threshold_1(self, output: LiteratureIntelligenceOutput) -> List[str]:
        """Soft threshold: Prefer cross-paper relationship coverage >= 70%"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer cross-paper relationship coverage >= 70%
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
