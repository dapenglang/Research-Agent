"""
Module 11 — Figure & Table Generation
Input/output validators.

Provides InputValidator and OutputValidator classes that enforce the
module's contract: hard requirements must pass, soft thresholds produce
warnings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# NOTE: Import from the local interface module
# from .interface import FigureTableInput, FigureTableOutput


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
    """Validator for Module 11 — Figure & Table Generation inputs.

    Input validation rules:
    - method_spec.json exists
    - paper_figure_plan.yaml exists with figures and tables
    - Data sources referenced in plan exist (synthetic_results/ or experiments/)
    """

    REQUIRED_FILES = ['method_spec.json', 'paper_figure_plan.yaml']
    OPTIONAL_FILES = ['synthetic_results/', 'experiments/<task_id>/', 'external data (xlsx/csv/json)']

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
        if "paper_figure_plan.yaml" not in input_files:
            result.add_error("Missing required input file: paper_figure_plan.yaml")

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
    """Validator for Module 11 — Figure & Table Generation outputs.

    Output validation rules:
    - All figure IDs from plan have SVG and PDF outputs
    - All table IDs from plan have at least 1 format output
    - captions.yaml covers all figure and table IDs
    - data_origin is set on all output files

    Hard requirements (must pass):
    - Every figure in paper_figure_plan has a corresponding output file
    - Every table in paper_figure_plan has a corresponding output file
    - captions.yaml has entries for all figures and tables
    - External data is tagged with data_origin='external'
    - Figures are produced in both SVG and PDF (vector formats)

    Soft thresholds (warnings):
    - Prefer source_data/ preserved for each figure
    - Prefer plotting_specs/ for reproducibility
    - Prefer raster/ versions for preview
    """

    REQUIRED_FILES = ['figures/*.svg', 'figures/*.pdf', 'figures/source_data/', 'figures/plotting_specs/', 'figures/raster/', 'tables/*.xlsx', 'tables/*.csv', 'tables/*.tex', 'captions/captions.yaml']

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
        if "figures/*.svg" not in output_files:
            result.add_error("Missing required output file: figures/*.svg")
        if "figures/*.pdf" not in output_files:
            result.add_error("Missing required output file: figures/*.pdf")
        if "figures/source_data/" not in output_files:
            result.add_error("Missing required output file: figures/source_data/")
        if "figures/plotting_specs/" not in output_files:
            result.add_error("Missing required output file: figures/plotting_specs/")
        if "figures/raster/" not in output_files:
            result.add_error("Missing required output file: figures/raster/")
        if "tables/*.xlsx" not in output_files:
            result.add_error("Missing required output file: tables/*.xlsx")
        if "tables/*.csv" not in output_files:
            result.add_error("Missing required output file: tables/*.csv")
        if "tables/*.tex" not in output_files:
            result.add_error("Missing required output file: tables/*.tex")
        if "captions/captions.yaml" not in output_files:
            result.add_error("Missing required output file: captions/captions.yaml")

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

    def _check_hard_requirement_0(self, output: FigureTableOutput) -> List[str]:
        """Hard requirement: Every figure in paper_figure_plan has a corresponding output file"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Every figure in paper_figure_plan has a corresponding output file
        return errors
    def _check_hard_requirement_1(self, output: FigureTableOutput) -> List[str]:
        """Hard requirement: Every table in paper_figure_plan has a corresponding output file"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Every table in paper_figure_plan has a corresponding output file
        return errors
    def _check_hard_requirement_2(self, output: FigureTableOutput) -> List[str]:
        """Hard requirement: captions.yaml has entries for all figures and tables"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: captions.yaml has entries for all figures and tables
        return errors
    def _check_hard_requirement_3(self, output: FigureTableOutput) -> List[str]:
        """Hard requirement: External data is tagged with data_origin='external'"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: External data is tagged with data_origin='external'
        return errors
    def _check_hard_requirement_4(self, output: FigureTableOutput) -> List[str]:
        """Hard requirement: Figures are produced in both SVG and PDF (vector formats)"""
        errors: List[str] = []
        # TODO: Implement actual validation logic
        # Requirement: Figures are produced in both SVG and PDF (vector formats)
        return errors

    def _check_soft_threshold_0(self, output: FigureTableOutput) -> List[str]:
        """Soft threshold: Prefer source_data/ preserved for each figure"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer source_data/ preserved for each figure
        return warnings
    def _check_soft_threshold_1(self, output: FigureTableOutput) -> List[str]:
        """Soft threshold: Prefer plotting_specs/ for reproducibility"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer plotting_specs/ for reproducibility
        return warnings
    def _check_soft_threshold_2(self, output: FigureTableOutput) -> List[str]:
        """Soft threshold: Prefer raster/ versions for preview"""
        warnings: List[str] = []
        # TODO: Implement actual validation logic
        # Threshold: Prefer raster/ versions for preview
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
