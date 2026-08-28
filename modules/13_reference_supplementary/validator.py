"""
Module 13 — Reference & Supplementary
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import ReferenceSupplementaryInput, ReferenceSupplementaryOutput


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
    """Validator for Module 13 — Reference & Supplementary inputs.

    Input validation rules:
    - paper/ directory exists with paper.md
    - paper_metadata.jsonl exists and is valid JSONL
    - At least 1 paper metadata entry exists
    """

    REQUIRED_FILES = ['paper/', 'paper_metadata.jsonl']
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
        if "paper/" not in input_files:
            result.add_error("Missing required input file: paper/")
        if "paper_metadata.jsonl" not in input_files:
            result.add_error("Missing required input file: paper_metadata.jsonl")

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
    """Validator for Module 13 — Reference & Supplementary outputs.

    Output validation rules:
    - references.bib entries match paper_metadata.jsonl
    - All in-text citations resolved in references.bib
    - citation_validation_report has matching totals
    - supplementary.tex is compilable LaTeX

    Hard requirements (must pass):
    - references.bib has at least 1 entry
    - citation_validation_report.md exists with citation counts
    - supplementary.tex is valid LaTeX
    - supplementary.docx is a valid Word file
    - All citations in paper/ have corresponding bib entries

    Soft thresholds (warnings):
    - Prefer 0 invalid citations
    - Prefer supplementary materials include appendix with full results
    """

    REQUIRED_FILES = ['references.bib', 'citation_validation_report.md', 'supplementary.tex', 'supplementary.docx']

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
        if "references.bib" not in output_files:
            result.add_error("Missing required output file: references.bib")
        if "citation_validation_report.md" not in output_files:
            result.add_error("Missing required output file: citation_validation_report.md")
        if "supplementary.tex" not in output_files:
            result.add_error("Missing required output file: supplementary.tex")
        if "supplementary.docx" not in output_files:
            result.add_error("Missing required output file: supplementary.docx")

        # Check output file contents (schema-level validation)
        for filename, filepath in output_files.items():
            file_errors = self._validate_file(filename, filepath)
            result.errors.extend(file_errors)

        # Run hard requirement checks
        result.merge(self._check_hard_requirement_0(output))
        result.merge(self._check_hard_requirement_1(output))
        result.merge(self._check_hard_requirement_2(output))
        result.merge(self._check_hard_requirement_3(output))
        result.merge(self._check_hard_requirement_4(output))

        # Run soft threshold checks
        thresh_result = self._check_soft_threshold_0(output)
        result.warnings.extend(thresh_result)
        thresh_result = self._check_soft_threshold_1(output)
        result.warnings.extend(thresh_result)

        if result.errors:
            result.is_valid = False

        return result

    def _check_hard_requirement_0(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Hard requirement: references.bib has at least 1 entry"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: references.bib has at least 1 entry
        return errors
    def _check_hard_requirement_1(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Hard requirement: citation_validation_report.md exists with citation counts"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: citation_validation_report.md exists with citation counts
        return errors
    def _check_hard_requirement_2(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Hard requirement: supplementary.tex is valid LaTeX"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: supplementary.tex is valid LaTeX
        return errors
    def _check_hard_requirement_3(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Hard requirement: supplementary.docx is a valid Word file"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: supplementary.docx is a valid Word file
        return errors
    def _check_hard_requirement_4(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Hard requirement: All citations in paper/ have corresponding bib entries"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: All citations in paper/ have corresponding bib entries
        return errors

    def _check_soft_threshold_0(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Soft threshold: Prefer 0 invalid citations"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer 0 invalid citations
        return warnings
    def _check_soft_threshold_1(self, output: ReferenceSupplementaryOutput) -> List[str]:
        """Soft threshold: Prefer supplementary materials include appendix with full results"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer supplementary materials include appendix with full results
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
