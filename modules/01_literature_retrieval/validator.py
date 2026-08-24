"""
Module 01 — Literature Retrieval
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import LiteratureRetrievalInput, LiteratureRetrievalOutput


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
    """Validator for Module 01 — Literature Retrieval inputs.

    Input validation rules:
    - research_task.yaml exists and is valid YAML
    - research_question is non-empty string
    - keywords list is non-empty
    """

    REQUIRED_FILES = ['research_task.yaml']
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
        if "research_task.yaml" not in input_files:
            result.add_error("Missing required input file: research_task.yaml")

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
    """Validator for Module 01 — Literature Retrieval outputs.

    Output validation rules:
    - paper_metadata.jsonl is valid JSONL with required fields
    - download_queue.json entries have paper_id, url, source_db
    - literature_manifest.json has total_papers matching jsonl count

    Hard requirements (must pass):
    - At least 1 paper metadata entry in paper_metadata.jsonl
    - research_task.yaml must contain a non-empty research_question
    - download_queue.json must have at least 1 entry

    Soft thresholds (warnings):
    - Prefer >= 20 papers retrieved for meaningful analysis
    - Prefer papers from >= 2 databases
    """

    REQUIRED_FILES = ['literature_manifest.json', 'paper_metadata.jsonl', 'download_queue.json', 'Module01_Validation_Report.md', 'module_manifest.json']

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
        if "literature_manifest.json" not in output_files:
            result.add_error("Missing required output file: literature_manifest.json")
        if "paper_metadata.jsonl" not in output_files:
            result.add_error("Missing required output file: paper_metadata.jsonl")
        if "download_queue.json" not in output_files:
            result.add_error("Missing required output file: download_queue.json")
        if "Module01_Validation_Report.md" not in output_files:
            result.add_error("Missing required output file: Module01_Validation_Report.md")
        if "module_manifest.json" not in output_files:
            result.add_error("Missing required output file: module_manifest.json")

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

    def _check_hard_requirement_0(self, output: LiteratureRetrievalOutput) -> List[str]:
        """Hard requirement: At least 1 paper metadata entry in paper_metadata.jsonl"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: At least 1 paper metadata entry in paper_metadata.jsonl
        return errors
    def _check_hard_requirement_1(self, output: LiteratureRetrievalOutput) -> List[str]:
        """Hard requirement: research_task.yaml must contain a non-empty research_question"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: research_task.yaml must contain a non-empty research_question
        return errors
    def _check_hard_requirement_2(self, output: LiteratureRetrievalOutput) -> List[str]:
        """Hard requirement: download_queue.json must have at least 1 entry"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: download_queue.json must have at least 1 entry
        return errors

    def _check_soft_threshold_0(self, output: LiteratureRetrievalOutput) -> List[str]:
        """Soft threshold: Prefer >= 20 papers retrieved for meaningful analysis"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 20 papers retrieved for meaningful analysis
        return warnings
    def _check_soft_threshold_1(self, output: LiteratureRetrievalOutput) -> List[str]:
        """Soft threshold: Prefer papers from >= 2 databases"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer papers from >= 2 databases
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
