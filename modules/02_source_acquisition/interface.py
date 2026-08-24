"""
Module 02 — Source Acquisition & Parsing
Interface contract definition.

This file defines the input/output dataclasses and the abstract interface
that any implementation of Module 02 must satisfy.

Upstream: 01
Downstream: 03
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SourceAcquisitionInput:
    """Standard input for Module 02 — Source Acquisition & Parsing.

    Required input files:
    - download_queue.json

    Optional input files:
    (none)
    """
    task_id: str
    config: Dict[str, Any]
    input_files: Dict[str, str]  # filename -> path
    context: Dict[str, Any]  # from upstream modules
    upstream_module_01: Dict[str, Any]  # outputs from Module 01


@dataclass
class SourceAcquisitionOutput:
    """Standard output for Module 02 — Source Acquisition & Parsing.

    Output files produced:
    - papers/<paper_id>/metadata.json
    - papers/<paper_id>/original.pdf
    - papers/<paper_id>/source/
    - papers/<paper_id>/normalized/paper.md
    - papers/<paper_id>/equations.json
    - papers/<paper_id>/figures.json
    - papers/<paper_id>/tables.json
    - papers/<paper_id>/citations.json
    - papers/<paper_id>/provenance.json
    """
    task_id: str
    output_files: Dict[str, str]  # filename -> path
    manifest: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class Module02Interface(ABC):
    """Interface contract for Module 02 — Source Acquisition & Parsing.

    Upstream:   01
    Downstream: 03

    This interface defines the lifecycle of Module 02:
    1. load_config       — Load and validate module configuration
    2. validate_input    — Verify all required inputs are present and valid
    3. execute           — Run the module's core logic
    4. validate_output   — Verify all required outputs are present and valid
    5. quality_assessment — Evaluate output quality against thresholds
    6. write_manifest    — Generate the module manifest for provenance
    7. write_report      — Generate a human-readable validation report
    """

    MODULE_ID = "02"
    MODULE_NAME = "Source Acquisition & Parsing"

    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load and validate module-specific configuration.

        Args:
            config: Configuration dictionary with module-specific parameters.
        """
        ...

    @abstractmethod
    def validate_input(self, input_data: SourceAcquisitionInput) -> bool:
        """Validate that all required inputs are present and well-formed.

        Args:
            input_data: Standard module input containing task_id, config,
                        input_files, and context from upstream modules.

        Returns:
            True if input is valid, False otherwise.
        """
        ...

    @abstractmethod
    def execute(self, input_data: SourceAcquisitionInput) -> SourceAcquisitionOutput:
        """Execute the module's core logic.

        Args:
            input_data: Validated module input.

        Returns:
            Module output containing output_files, manifest, warnings, errors.
        """
        ...

    @abstractmethod
    def validate_output(self, output: SourceAcquisitionOutput) -> bool:
        """Validate that all required outputs are present and well-formed.

        Args:
            output: Module output to validate.

        Returns:
            True if output is valid, False otherwise.
        """
        ...

    @abstractmethod
    def quality_assessment(self, output: SourceAcquisitionOutput) -> Dict[str, Any]:
        """Assess output quality against hard requirements and soft thresholds.

        Args:
            output: Module output to assess.

        Returns:
            Dictionary with quality metrics, pass/fail status, and details.
        """
        ...

    @abstractmethod
    def write_manifest(self, output: SourceAcquisitionOutput) -> Dict[str, Any]:
        """Generate the module manifest for provenance tracking.

        Args:
            output: Module output.

        Returns:
            Manifest dictionary with module_id, version, inputs, outputs,
            timestamps, and quality metrics.
        """
        ...

    @abstractmethod
    def write_report(self, output: SourceAcquisitionOutput) -> str:
        """Generate a human-readable validation report.

        Args:
            output: Module output.

        Returns:
            Markdown-formatted report string.
        """
        ...
