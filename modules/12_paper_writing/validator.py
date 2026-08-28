"""
Module 12 — Paper Writing
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import PaperWritingInput, PaperWritingOutput


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
    """Validator for Module 12 — Paper Writing inputs.

    Input validation rules:
    - figures/ exists with at least 1 figure
    - tables/ exists with at least 1 table
    - scientific_result_analysis.md exists
    - method_spec.json exists
    """

    REQUIRED_FILES = ['figures/', 'tables/', 'method_spec.json', 'scientific_result_analysis.md']
    OPTIONAL_FILES = ['paper_style_profile.json', 'research_landscape.md', 'theory_framework.md', 'experiment_plan.md']

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
        if "figures/" not in input_files:
            result.add_error("Missing required input file: figures/")
        if "tables/" not in input_files:
            result.add_error("Missing required input file: tables/")
        if "method_spec.json" not in input_files:
            result.add_error("Missing required input file: method_spec.json")
        if "scientific_result_analysis.md" not in input_files:
            result.add_error("Missing required input file: scientific_result_analysis.md")

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
    """Validator for Module 12 — Paper Writing outputs.

    Output validation rules:
    - paper.md has title, abstract, sections
    - latex/main.tex is valid LaTeX
    - word/paper.docx is a valid Word file
    - Figure references in paper match figures/ directory
    - Table references in paper match tables/ directory

    Hard requirements (must pass):
    - paper.md exists with title, abstract, and at least 4 sections
    - latex/main.tex exists and is compilable
    - word/paper.docx exists
    - All three formats (Markdown, LaTeX, Word) are produced
    - All figure and table references in text have corresponding files

    Soft thresholds (warnings):
    - Prefer paper_style_profile.json applied consistently
    - Prefer LaTeX Makefile for easy compilation
    - Prefer abstract <= 250 words
    """

    REQUIRED_FILES = ['paper/paper.md', 'paper/latex/', 'paper/word/']

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
        if "paper/paper.md" not in output_files:
            result.add_error("Missing required output file: paper/paper.md")
        if "paper/latex/" not in output_files:
            result.add_error("Missing required output file: paper/latex/")
        if "paper/word/" not in output_files:
            result.add_error("Missing required output file: paper/word/")

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
        thresh_result = self._check_soft_threshold_2(output)
        result.warnings.extend(thresh_result)

        if result.errors:
            result.is_valid = False

        return result

    def _check_hard_requirement_0(self, output: PaperWritingOutput) -> List[str]:
        """Hard requirement: paper.md exists with title, abstract, and at least 4 sections"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: paper.md exists with title, abstract, and at least 4 sections
        return errors
    def _check_hard_requirement_1(self, output: PaperWritingOutput) -> List[str]:
        """Hard requirement: latex/main.tex exists and is compilable"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: latex/main.tex exists and is compilable
        return errors
    def _check_hard_requirement_2(self, output: PaperWritingOutput) -> List[str]:
        """Hard requirement: word/paper.docx exists"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: word/paper.docx exists
        return errors
    def _check_hard_requirement_3(self, output: PaperWritingOutput) -> List[str]:
        """Hard requirement: All three formats (Markdown, LaTeX, Word) are produced"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: All three formats (Markdown, LaTeX, Word) are produced
        return errors
    def _check_hard_requirement_4(self, output: PaperWritingOutput) -> List[str]:
        """Hard requirement: All figure and table references in text have corresponding files"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: All figure and table references in text have corresponding files
        return errors

    def _check_soft_threshold_0(self, output: PaperWritingOutput) -> List[str]:
        """Soft threshold: Prefer paper_style_profile.json applied consistently"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer paper_style_profile.json applied consistently
        return warnings
    def _check_soft_threshold_1(self, output: PaperWritingOutput) -> List[str]:
        """Soft threshold: Prefer LaTeX Makefile for easy compilation"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer LaTeX Makefile for easy compilation
        return warnings
    def _check_soft_threshold_2(self, output: PaperWritingOutput) -> List[str]:
        """Soft threshold: Prefer abstract <= 250 words"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer abstract <= 250 words
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
