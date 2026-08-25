"""
Module 04 — Research Landscape & Gap Analysis
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import ResearchLandscapeInput, ResearchLandscapeOutput


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
    """Validator for Module 04 — Research Landscape & Gap Analysis inputs.

    Input validation rules:
    - paper_analysis.json exists and is valid JSON
    - At least 3 paper analyses present for meaningful landscape
    """

    REQUIRED_FILES = ['paper_analysis.json']
    OPTIONAL_FILES = ['literature_analysis_index.jsonl']

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
        if "paper_analysis.json" not in input_files:
            result.add_error("Missing required input file: paper_analysis.json")

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
    """Validator for Module 04 — Research Landscape & Gap Analysis outputs.

    Output validation rules:
    - taxonomy.json categories reference valid paper_ids
    - gap_candidates have supporting_papers from input set
    - contradiction_map references valid paper pairs

    Hard requirements (must pass):
    - taxonomy.json has at least 1 category
    - gap_candidates.json has at least 1 gap
    - research_landscape.md is non-empty

    Soft thresholds (warnings):
    - Prefer >= 3 gap candidates identified
    - Prefer >= 2 contradictions mapped
    """

    REQUIRED_FILES = ['research_landscape.md', 'taxonomy.json', 'trend_analysis.json', 'contradiction_map.json', 'gap_candidates.json']

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
        if "research_landscape.md" not in output_files:
            result.add_error("Missing required output file: research_landscape.md")
        if "taxonomy.json" not in output_files:
            result.add_error("Missing required output file: taxonomy.json")
        if "trend_analysis.json" not in output_files:
            result.add_error("Missing required output file: trend_analysis.json")
        if "contradiction_map.json" not in output_files:
            result.add_error("Missing required output file: contradiction_map.json")
        if "gap_candidates.json" not in output_files:
            result.add_error("Missing required output file: gap_candidates.json")

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

    def _check_hard_requirement_0(self, output: ResearchLandscapeOutput) -> List[str]:
        """Hard requirement: taxonomy.json has at least 1 category"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: taxonomy.json has at least 1 category
        return errors
    def _check_hard_requirement_1(self, output: ResearchLandscapeOutput) -> List[str]:
        """Hard requirement: gap_candidates.json has at least 1 gap"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: gap_candidates.json has at least 1 gap
        return errors
    def _check_hard_requirement_2(self, output: ResearchLandscapeOutput) -> List[str]:
        """Hard requirement: research_landscape.md is non-empty"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: research_landscape.md is non-empty
        return errors

    def _check_soft_threshold_0(self, output: ResearchLandscapeOutput) -> List[str]:
        """Soft threshold: Prefer >= 3 gap candidates identified"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 3 gap candidates identified
        return warnings
    def _check_soft_threshold_1(self, output: ResearchLandscapeOutput) -> List[str]:
        """Soft threshold: Prefer >= 2 contradictions mapped"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 2 contradictions mapped
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
