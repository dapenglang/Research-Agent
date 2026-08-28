"""
Module 10 — Scientific Result Analysis
Interface contract definition.

This file defines the input/output dataclasses and the abstract interface
that any implementation of Module 10 must satisfy.

Upstream: 07, 08, 09
Downstream: 11
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ResultAnalysisInput:
    """Standard input for Module 10 — Scientific Result Analysis.

    Required input files:
    - synthetic_results/
    - claim_evidence_plan.json

    Optional input files:
    - experiments/<task_id>/
    """
    task_id: str
    config: Dict[str, Any]
    input_files: Dict[str, str]  # filename -> path
    context: Dict[str, Any]  # from upstream modules
    upstream_module_07: Dict[str, Any]  # outputs from Module 07
    upstream_module_08: Dict[str, Any]  # outputs from Module 08
    upstream_module_09: Dict[str, Any]  # outputs from Module 09


@dataclass
class ResultAnalysisOutput:
    """Standard output for Module 10 — Scientific Result Analysis.

    Output files produced:
    - scientific_result_analysis.md
    - claim_evidence_mapping.md
    - revision_recommendation.md
    - decision.json
    """
    task_id: str
    output_files: Dict[str, str]  # filename -> path
    manifest: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

# Decision routing: PASS_TO_FIGURE_TABLE, RETURN_TO_EXPERIMENT, RETURN_TO_EXPERIMENT_PLAN, RETURN_TO_METHOD, RETURN_TO_INNOVATION, HUMAN_REVIEW_REQUIRED


class Module10Interface(ABC):
    """Interface contract for Module 10 — Scientific Result Analysis.

    Upstream:   07, 08, 09
    Downstream: 11

    This interface defines the lifecycle of Module 10:
    1. load_config       — Load and validate module configuration
    2. validate_input    — Verify all required inputs are present and valid
    3. execute           — Run the module's core logic
    4. validate_output   — Verify all required outputs are present and valid
    5. quality_assessment — Evaluate output quality against thresholds
    6. write_manifest    — Generate the module manifest for provenance
    7. write_report      — Generate a human-readable validation report
    """

    MODULE_ID = "10"
    MODULE_NAME = "Scientific Result Analysis"

    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load and validate module-specific configuration.

        Args:
            config: Configuration dictionary with module-specific parameters.
        """
        ...

    @abstractmethod
    def validate_input(self, input_data: ResultAnalysisInput) -> bool:
        """Validate that all required inputs are present and well-formed.

        Args:
            input_data: Standard module input containing task_id, config,
                        input_files, and context from upstream modules.

        Returns:
            True if input is valid, False otherwise.
        """
        ...

    @abstractmethod
    def execute(self, input_data: ResultAnalysisInput) -> ResultAnalysisOutput:
        """Execute the module's core logic.

        Args:
            input_data: Validated module input.

        Returns:
            Module output containing output_files, manifest, warnings, errors.
        """
        ...

    @abstractmethod
    def validate_output(self, output: ResultAnalysisOutput) -> bool:
        """Validate that all required outputs are present and well-formed.

        Args:
            output: Module output to validate.

        Returns:
            True if output is valid, False otherwise.
        """
        ...

    @abstractmethod
    def quality_assessment(self, output: ResultAnalysisOutput) -> Dict[str, Any]:
        """Assess output quality against hard requirements and soft thresholds.

        Args:
            output: Module output to assess.

        Returns:
            Dictionary with quality metrics, pass/fail status, and details.
        """
        ...

    @abstractmethod
    def write_manifest(self, output: ResultAnalysisOutput) -> Dict[str, Any]:
        """Generate the module manifest for provenance tracking.

        Args:
            output: Module output.

        Returns:
            Manifest dictionary with module_id, version, inputs, outputs,
            timestamps, and quality metrics.
        """
        ...

    @abstractmethod
    def write_report(self, output: ResultAnalysisOutput) -> str:
        """Generate a human-readable validation report.

        Args:
            output: Module output.

        Returns:
            Markdown-formatted report string.
        """
        ...
