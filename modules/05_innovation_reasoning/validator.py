"""
Module 05 — Innovation & Novelty Reasoning
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import InnovationReasoningInput, InnovationReasoningOutput


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
    """Validator for Module 05 — Innovation & Novelty Reasoning inputs.

    Input validation rules:
    - gap_candidates.json exists with at least 1 gap
    - paper_analysis.json exists with at least 1 analysis
    """

    REQUIRED_FILES = ['gap_candidates.json', 'paper_analysis.json']
    OPTIONAL_FILES = ['contradiction_map.json', 'trend_analysis.json']

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
        if "gap_candidates.json" not in input_files:
            result.add_error("Missing required input file: gap_candidates.json")
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
    """Validator for Module 05 — Innovation & Novelty Reasoning outputs.

    Output validation rules:
    - innovation_candidates.json has candidates with all score fields
    - final_research_direction.md references a candidate from the list
    - Scores are in [0.0, 1.0] range

    Hard requirements (must pass):
    - At least 1 innovation candidate generated
    - final_research_direction.md has selected_direction and justification
    - Every candidate has novelty_score and feasibility_score

    Soft thresholds (warnings):
    - Prefer >= 3 innovation candidates evaluated
    - Prefer top candidate novelty_score >= 0.7
    """

    REQUIRED_FILES = ['innovation_candidates.json', 'novelty_analysis.md', 'final_research_direction.md']

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
        if "innovation_candidates.json" not in output_files:
            result.add_error("Missing required output file: innovation_candidates.json")
        if "novelty_analysis.md" not in output_files:
            result.add_error("Missing required output file: novelty_analysis.md")
        if "final_research_direction.md" not in output_files:
            result.add_error("Missing required output file: final_research_direction.md")

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

    def _check_hard_requirement_0(self, output: InnovationReasoningOutput) -> List[str]:
        """Hard requirement: At least 1 innovation candidate generated"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: At least 1 innovation candidate generated
        return errors
    def _check_hard_requirement_1(self, output: InnovationReasoningOutput) -> List[str]:
        """Hard requirement: final_research_direction.md has selected_direction and justification"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: final_research_direction.md has selected_direction and justification
        return errors
    def _check_hard_requirement_2(self, output: InnovationReasoningOutput) -> List[str]:
        """Hard requirement: Every candidate has novelty_score and feasibility_score"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Every candidate has novelty_score and feasibility_score
        return errors

    def _check_soft_threshold_0(self, output: InnovationReasoningOutput) -> List[str]:
        """Soft threshold: Prefer >= 3 innovation candidates evaluated"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 3 innovation candidates evaluated
        return warnings
    def _check_soft_threshold_1(self, output: InnovationReasoningOutput) -> List[str]:
        """Soft threshold: Prefer top candidate novelty_score >= 0.7"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer top candidate novelty_score >= 0.7
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
