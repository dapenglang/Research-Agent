"""Base module contract defining the standard module lifecycle.

Every pipeline module in Research Agent v3 must subclass ``ModuleContract``
and implement its abstract methods.  The orchestrator calls these methods in
a fixed order so that configuration, validation, execution, quality
assessment, and reporting are consistent across modules.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModuleStatus(str, Enum):
    """Outcome status for a module execution or validation step."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCKED = "blocked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    SKIPPED = "skipped"


@dataclass
class ModuleManifest:
    """Schema for ``module_manifest.json`` written by each module.

    The manifest is a machine-readable record of what the module consumed,
    what it produced, and whether it passed validation.
    """

    module_id: str
    task_id: str
    status: ModuleStatus = ModuleStatus.PASS
    started_at: str = ""
    finished_at: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    next_recommended_module: Optional[str] = None
    manifest_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the manifest to a plain dict suitable for JSON."""
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def to_json(self, path: str | Path) -> None:
        """Write the manifest as a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleManifest":
        """Reconstruct a manifest from a plain dict (e.g. loaded from JSON)."""
        raw_status = data.get("status", ModuleStatus.PASS)
        if isinstance(raw_status, str):
            raw_status = ModuleStatus(raw_status)
        return cls(
            module_id=data["module_id"],
            task_id=data["task_id"],
            status=raw_status,
            started_at=data.get("started_at", ""),
            finished_at=data.get("finished_at", ""),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            quality_score=data.get("quality_score"),
            warnings=data.get("warnings", []),
            errors=data.get("errors", []),
            config_snapshot=data.get("config_snapshot", {}),
            next_recommended_module=data.get("next_recommended_module"),
            manifest_version=data.get("manifest_version", "1.0"),
        )


class ModuleContract(ABC):
    """Abstract base class that every pipeline module must implement.

    The lifecycle is::

        load_config -> validate_input -> execute -> validate_output
                                   -> quality_assessment
                                   -> write_manifest -> write_report
    """

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Unique identifier for this module (e.g. ``"01_literature_retrieval"``)."""
        ...

    @abstractmethod
    def load_config(self, config_path: str | Path) -> Dict[str, Any]:
        """Load and parse the module-specific configuration file.

        Args:
            config_path: Path to a YAML or JSON config file.

        Returns:
            Parsed configuration as a dictionary.
        """
        ...

    @abstractmethod
    def validate_input(self, inputs: Dict[str, Any]) -> ModuleStatus:
        """Verify that all required input files and fields are present.

        Args:
            inputs: Mapping of input names to file paths or values.

        Returns:
            ``ModuleStatus.PASS`` if all inputs are valid, otherwise
            ``ModuleStatus.FAIL`` or ``ModuleStatus.WARNING``.
        """
        ...

    @abstractmethod
    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Run the core logic of the module.

        Args:
            inputs: Validated input mapping.
            config: Module configuration loaded by ``load_config``.

        Returns:
            Dictionary of output artefacts (file paths, computed values, etc.).
        """
        ...

    @abstractmethod
    def validate_output(self, outputs: Dict[str, Any]) -> ModuleStatus:
        """Verify that the module produced all expected output artefacts.

        Args:
            outputs: The dictionary returned by ``execute``.

        Returns:
            ``ModuleStatus.PASS`` if outputs are complete and well-formed.
        """
        ...

    @abstractmethod
    def quality_assessment(self, outputs: Dict[str, Any]) -> tuple[ModuleStatus, float]:
        """Evaluate quality metrics against hard requirements and soft thresholds.

        Args:
            outputs: The dictionary returned by ``execute``.

        Returns:
            A tuple of ``(status, score)`` where *score* is a float in
            ``[0.0, 1.0]``.
        """
        ...

    @abstractmethod
    def write_manifest(self, task_id: str, output_dir: str | Path) -> ModuleManifest:
        """Write ``module_manifest.json`` for this module run.

        Args:
            task_id: The parent research task identifier.
            output_dir: Directory where the manifest should be written.

        Returns:
            The :class:`ModuleManifest` that was written.
        """
        ...

    @abstractmethod
    def write_report(self, task_id: str, output_dir: str | Path) -> str:
        """Write a human-readable report (Markdown) for this module run.

        Args:
            task_id: The parent research task identifier.
            output_dir: Directory where the report should be written.

        Returns:
            Path to the written report file.
        """
        ...

    # ------------------------------------------------------------------
    # Convenience helpers (non-abstract)
    # ------------------------------------------------------------------

    def _now_iso(self) -> str:
        """Return the current UTC time in ISO-8601 format."""
        return datetime.now(timezone.utc).isoformat()

    def run_full_lifecycle(
        self,
        task_id: str,
        inputs: Dict[str, Any],
        config_path: str | Path,
        output_dir: str | Path,
    ) -> ModuleManifest:
        """Execute the complete module lifecycle in the standard order.

        This is a convenience method that chains all abstract methods and
        writes the manifest and report.  Subclasses may override it for
        custom control flow, but the default implementation should suffice
        for most modules.
        """
        config = self.load_config(config_path)

        input_status = self.validate_input(inputs)
        if input_status == ModuleStatus.FAIL:
            manifest = ModuleManifest(
                module_id=self.module_id,
                task_id=task_id,
                status=ModuleStatus.FAIL,
                started_at=self._now_iso(),
                finished_at=self._now_iso(),
                errors=["Input validation failed"],
            )
            manifest.to_json(Path(output_dir) / "module_manifest.json")
            return manifest

        outputs = self.execute(inputs, config)

        output_status = self.validate_output(outputs)
        quality_status, quality_score = self.quality_assessment(outputs)

        # Determine the overall status: the worse of the two.
        if output_status == ModuleStatus.FAIL or quality_status == ModuleStatus.FAIL:
            overall = ModuleStatus.FAIL
        elif output_status == ModuleStatus.WARNING or quality_status == ModuleStatus.WARNING:
            overall = ModuleStatus.WARNING
        else:
            overall = ModuleStatus.PASS

        manifest = ModuleManifest(
            module_id=self.module_id,
            task_id=task_id,
            status=overall,
            started_at=self._now_iso(),
            finished_at=self._now_iso(),
            outputs=list(outputs.keys()),
            quality_score=quality_score,
        )
        manifest.to_json(Path(output_dir) / "module_manifest.json")
        self.write_report(task_id, output_dir)
        return manifest
