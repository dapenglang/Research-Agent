"""
Module 02 — Source Acquisition & Parsing
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import SourceAcquisitionInput, SourceAcquisitionOutput


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
    """Validator for Module 02 — Source Acquisition & Parsing inputs.

    Input validation rules:
    - download_queue.json exists and is valid JSON
    - Queue is non-empty
    - Each queue entry has paper_id, url, source_db
    """

    REQUIRED_FILES = ['download_queue.json']
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
        if "download_queue.json" not in input_files:
            result.add_error("Missing required input file: download_queue.json")

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
    """Validator for Module 02 — Source Acquisition & Parsing outputs.

    Output validation rules:
    - normalized/paper.md is non-empty for each paper
    - provenance.json has download_timestamp and source_hash
    - metadata.json matches paper_id from download queue

    Hard requirements (must pass):
    - Every paper in download_queue must have a normalized/paper.md
    - provenance.json must exist for every downloaded paper
    - original.pdf must exist for every paper (unless open-access-only)

    Soft thresholds (warnings):
    - Prefer >= 80% of queue papers successfully downloaded
    - Prefer equation/figure/table extraction success rate >= 70%
    """

    REQUIRED_FILES = ['papers/<paper_id>/metadata.json', 'papers/<paper_id>/original.pdf', 'papers/<paper_id>/source/', 'papers/<paper_id>/normalized/paper.md', 'papers/<paper_id>/equations.json', 'papers/<paper_id>/figures.json', 'papers/<paper_id>/tables.json', 'papers/<paper_id>/citations.json', 'papers/<paper_id>/provenance.json']

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
        if "papers/<paper_id>/metadata.json" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/metadata.json")
        if "papers/<paper_id>/original.pdf" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/original.pdf")
        if "papers/<paper_id>/source/" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/source/")
        if "papers/<paper_id>/normalized/paper.md" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/normalized/paper.md")
        if "papers/<paper_id>/equations.json" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/equations.json")
        if "papers/<paper_id>/figures.json" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/figures.json")
        if "papers/<paper_id>/tables.json" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/tables.json")
        if "papers/<paper_id>/citations.json" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/citations.json")
        if "papers/<paper_id>/provenance.json" not in output_files:
            result.add_error("Missing required output file: papers/<paper_id>/provenance.json")

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

    def _check_hard_requirement_0(self, output: SourceAcquisitionOutput) -> List[str]:
        """Hard requirement: Every paper in download_queue must have a normalized/paper.md"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Every paper in download_queue must have a normalized/paper.md
        return errors
    def _check_hard_requirement_1(self, output: SourceAcquisitionOutput) -> List[str]:
        """Hard requirement: provenance.json must exist for every downloaded paper"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: provenance.json must exist for every downloaded paper
        return errors
    def _check_hard_requirement_2(self, output: SourceAcquisitionOutput) -> List[str]:
        """Hard requirement: original.pdf must exist for every paper (unless open-access-only)"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: original.pdf must exist for every paper (unless open-access-only)
        return errors

    def _check_soft_threshold_0(self, output: SourceAcquisitionOutput) -> List[str]:
        """Soft threshold: Prefer >= 80% of queue papers successfully downloaded"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 80% of queue papers successfully downloaded
        return warnings
    def _check_soft_threshold_1(self, output: SourceAcquisitionOutput) -> List[str]:
        """Soft threshold: Prefer equation/figure/table extraction success rate >= 70%"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer equation/figure/table extraction success rate >= 70%
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
