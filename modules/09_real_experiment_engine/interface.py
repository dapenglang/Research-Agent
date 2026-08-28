"""
Module 09 — Real Experiment Engine
Interface contract definition.

This file defines the input/output dataclasses and the abstract interface
that any implementation of Module 09 must satisfy.

Upstream: 06, 07
Downstream: 10, 11
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class RealExperimentInput:
    """Standard input for Module 09 — Real Experiment Engine.

    Required input files:
    - method_spec.json
    - experiment_matrix.yaml
    - claim_evidence_plan.json

    Optional input files:
    (none)
    """
    task_id: str
    config: Dict[str, Any]
    input_files: Dict[str, str]  # filename -> path
    context: Dict[str, Any]  # from upstream modules
    upstream_module_06: Dict[str, Any]  # outputs from Module 06
    upstream_module_07: Dict[str, Any]  # outputs from Module 07


@dataclass
class RealExperimentOutput:
    """Standard output for Module 09 — Real Experiment Engine.

    Output files produced:
    - experiments/<task_id>/config/
    - experiments/<task_id>/code/
    - experiments/<task_id>/checkpoints/
    - experiments/<task_id>/raw_results/
    - experiments/<task_id>/processed_results/
    - experiments/<task_id>/logs/
    - experiments/<task_id>/environment/
    - experiments/<task_id>/provenance/
    """
    task_id: str
    output_files: Dict[str, str]  # filename -> path
    manifest: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

# NOTE: SAMRA is an adapter/plugin, NOT built into this module.


class Module09Interface(ABC):
    """Interface contract for Module 09 — Real Experiment Engine.

    Upstream:   06, 07
    Downstream: 10, 11

    This interface defines the lifecycle of Module 09:
    1. load_config       — Load and validate module configuration
    2. validate_input    — Verify all required inputs are present and valid
    3. execute           — Run the module's core logic
    4. validate_output   — Verify all required outputs are present and valid
    5. quality_assessment — Evaluate output quality against thresholds
    6. write_manifest    — Generate the module manifest for provenance
    7. write_report      — Generate a human-readable validation report
    """

    MODULE_ID = "09"
    MODULE_NAME = "Real Experiment Engine"

    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> None:
        """Load and validate module-specific configuration.

        Args:
            config: Configuration dictionary with module-specific parameters.
        """
        ...

    @abstractmethod
    def validate_input(self, input_data: RealExperimentInput) -> bool:
        """Validate that all required inputs are present and well-formed.

        Args:
            input_data: Standard module input containing task_id, config,
                        input_files, and context from upstream modules.

        Returns:
            True if input is valid, False otherwise.
        """
        ...

    @abstractmethod
    def execute(self, input_data: RealExperimentInput) -> RealExperimentOutput:
        """Execute the module's core logic.

        Args:
            input_data: Validated module input.

        Returns:
            Module output containing output_files, manifest, warnings, errors.
        """
        ...

    @abstractmethod
    def validate_output(self, output: RealExperimentOutput) -> bool:
        """Validate that all required outputs are present and well-formed.

        Args:
            output: Module output to validate.

        Returns:
            True if output is valid, False otherwise.
        """
        ...

    @abstractmethod
    def quality_assessment(self, output: RealExperimentOutput) -> Dict[str, Any]:
        """Assess output quality against hard requirements and soft thresholds.

        Args:
            output: Module output to assess.

        Returns:
            Dictionary with quality metrics, pass/fail status, and details.
        """
        ...

    @abstractmethod
    def write_manifest(self, output: RealExperimentOutput) -> Dict[str, Any]:
        """Generate the module manifest for provenance tracking.

        Args:
            output: Module output.

        Returns:
            Manifest dictionary with module_id, version, inputs, outputs,
            timestamps, and quality metrics.
        """
        ...

    @abstractmethod
    def write_report(self, output: RealExperimentOutput) -> str:
        """Generate a human-readable validation report.

        Args:
            output: Module output.

        Returns:
            Markdown-formatted report string.
        """
        ...
