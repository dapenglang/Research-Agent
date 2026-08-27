"""
Module 06 — Theory & Method Design
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import TheoryMethodInput, TheoryMethodOutput


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
    """Validator for Module 06 — Theory & Method Design inputs.

    Input validation rules:
    - final_research_direction.md exists and is non-empty
    - selected_direction is present
    """

    REQUIRED_FILES = ['final_research_direction.md']
    OPTIONAL_FILES = ['innovation_candidates.json']

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
        if "final_research_direction.md" not in input_files:
            result.add_error("Missing required input file: final_research_direction.md")

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
    """Validator for Module 06 — Theory & Method Design outputs.

    Output validation rules:
    - method_spec.json components are non-empty
    - Each algorithm has pseudocode
    - Each equation has LaTeX representation

    Hard requirements (must pass):
    - method_spec.json has method_name, components, input_schema, output_schema
    - theory_framework.md has assumptions and propositions
    - mathematical_formulation.md has at least 1 equation with LaTeX
    - algorithm_design.md has at least 1 algorithm with pseudocode

    Soft thresholds (warnings):
    - Prefer complexity analysis for each algorithm
    - Prefer >= 3 mathematical equations formalized
    """

    REQUIRED_FILES = ['method_spec.json', 'theory_framework.md', 'method_design.md', 'mathematical_formulation.md', 'algorithm_design.md']

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
        if "method_spec.json" not in output_files:
            result.add_error("Missing required output file: method_spec.json")
        if "theory_framework.md" not in output_files:
            result.add_error("Missing required output file: theory_framework.md")
        if "method_design.md" not in output_files:
            result.add_error("Missing required output file: method_design.md")
        if "mathematical_formulation.md" not in output_files:
            result.add_error("Missing required output file: mathematical_formulation.md")
        if "algorithm_design.md" not in output_files:
            result.add_error("Missing required output file: algorithm_design.md")

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

    def _check_hard_requirement_0(self, output: TheoryMethodOutput) -> List[str]:
        """Hard requirement: method_spec.json has method_name, components, input_schema, output_schema"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: method_spec.json has method_name, components, input_schema, output_schema
        return errors
    def _check_hard_requirement_1(self, output: TheoryMethodOutput) -> List[str]:
        """Hard requirement: theory_framework.md has assumptions and propositions"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: theory_framework.md has assumptions and propositions
        return errors
    def _check_hard_requirement_2(self, output: TheoryMethodOutput) -> List[str]:
        """Hard requirement: mathematical_formulation.md has at least 1 equation with LaTeX"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: mathematical_formulation.md has at least 1 equation with LaTeX
        return errors
    def _check_hard_requirement_3(self, output: TheoryMethodOutput) -> List[str]:
        """Hard requirement: algorithm_design.md has at least 1 algorithm with pseudocode"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: algorithm_design.md has at least 1 algorithm with pseudocode
        return errors

    def _check_soft_threshold_0(self, output: TheoryMethodOutput) -> List[str]:
        """Soft threshold: Prefer complexity analysis for each algorithm"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer complexity analysis for each algorithm
        return warnings
    def _check_soft_threshold_1(self, output: TheoryMethodOutput) -> List[str]:
        """Soft threshold: Prefer >= 3 mathematical equations formalized"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer >= 3 mathematical equations formalized
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
