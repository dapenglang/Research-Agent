"""
Module 03 — Literature Intelligence
Interface contract definition.

This file defines the input/output dataclasses and the abstract interface
that any implementation of Module 03 must satisfy.

Upstream: 02
Downstream: 04, 05
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class LiteratureIntelligenceInput:
    """Standard input for Module 03 — Literature Intelligence.

    Required input files:
    - papers/<paper_id>/normalized/paper.md

    Optional input files:
    - papers/<paper_id>/equations.json
    - papers/<paper_id>/figures.json
    - papers/<paper_id>/tables.json
    """
    task_id: str
    config: Dict[str, Any]
    input_files: Dict[str, str]  # filename -> path
    context: Dict[str, Any]  # from upstream modules
    upstream_module_02: Dict[str, Any]  # outputs from Module 02


@dataclass
class LiteratureIntelligenceOutput:
    """Standard output for Module 03 — Literature Intelligence.

    Output files produced:
    - paper_analysis.json
    - paper_analysis.md
    - literature_analysis_index.jsonl
    - Module03_Validation_Report.md
    """
    task_id: str
    output_files: Dict[str, str]  # filename -> path
    manifest: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class Module03Interface(ABC):
    """Interface contract for Module 03 — Literature Intelligence.

    Upstream:   02
    Downstream: 04, 05

    This interface defines the lifecycle of Module 03:
    1. load_config       — Load and validate module configuration
    2. validate_input    — Verify all required inputs are present and valid
    3. execute           — Run the module's core logic
    4. validate_output   — Verify all required outputs are present and valid
    5. quality_assessment — Evaluate output quality against thresholds
    6. write_manifest    — Generate the module manifest for provenance
    7. write_report      — Generate a human-readable validation report
    """

    MODULE_ID = "03"
    MODULE_NAME = "Literature Intelligence"

    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load and validate module-specific configuration.

        Args:
            config: Configuration dictionary with module-specific parameters.
        """
        ...

    @abstractmethod
    def validate_input(self, input_data: LiteratureIntelligenceInput) -> bool:
        """Validate that all required inputs are present and well-formed.

        Args:
            input_data: Standard module input containing task_id, config,
                        input_files, and context from upstream modules.

        Returns:
            True if input is valid, False otherwise.
        """
        ...

    @abstractmethod
    def execute(self, input_data: LiteratureIntelligenceInput) -> LiteratureIntelligenceOutput:
        """Execute the module's core logic.

        Args:
            input_data: Validated module input.

        Returns:
            Module output containing output_files, manifest, warnings, errors.
        """
        ...

    @abstractmethod
    def validate_output(self, output: LiteratureIntelligenceOutput) -> bool:
        """Validate that all required outputs are present and well-formed.

        Args:
            output: Module output to validate.

        Returns:
            True if output is valid, False otherwise.
        """
        ...

    @abstractmethod
    def quality_assessment(self, output: LiteratureIntelligenceOutput) -> Dict[str, Any]:
        """Assess output quality against hard requirements and soft thresholds.

        Args:
            output: Module output to assess.

        Returns:
            Dictionary with quality metrics, pass/fail status, and details.
        """
        ...

    @abstractmethod
    def write_manifest(self, output: LiteratureIntelligenceOutput) -> Dict[str, Any]:
        """Generate the module manifest for provenance tracking.

        Args:
            output: Module output.

        Returns:
            Manifest dictionary with module_id, version, inputs, outputs,
            timestamps, and quality metrics.
        """
        ...

    @abstractmethod
    def write_report(self, output: LiteratureIntelligenceOutput) -> str:
        """Generate a human-readable validation report.

        Args:
            output: Module output.

        Returns:
            Markdown-formatted report string.
        """
        ...
