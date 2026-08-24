"""Cross-module data contract.

Defines the standard structure that every piece of data flowing between
modules must carry, so that downstream modules can verify provenance and
origin before consuming it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class DataOrigin(str, Enum):
    """Where a piece of data originally came from.

    This is critical for preventing synthetic/mock/LLM-generated data from
    being mistaken for real experimental results.
    """

    REAL = "real"
    SYNTHETIC = "synthetic"
    MOCK = "mock"
    EXTERNAL = "external"
    MANUAL = "manual"


@dataclass
class Provenance:
    """Record of how a piece of data was produced.

    Attributes:
        source_files: Paths to the original source files (papers, datasets, etc.).
        transformations: Ordered list of transformation step descriptions.
        timestamp: When this provenance record was created.
        module_chain: Ordered list of module IDs that handled this data.
    """

    source_files: List[str] = field(default_factory=list)
    transformations: List[str] = field(default_factory=list)
    timestamp: str = ""
    module_chain: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def add_transformation(self, description: str, module_id: str) -> None:
        """Append a transformation step and the module that performed it."""
        self.transformations.append(description)
        self.module_chain.append(module_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict."""
        return asdict(self)


class DataContract:
    """Base class for cross-module data contracts.

    Every artefact passed between modules should be wrapped in or accompanied
    by a ``DataContract`` so the receiver can check origin and provenance.
    """

    def __init__(
        self,
        task_id: str,
        producer_module: str,
        provenance: Provenance,
        data_origin: DataOrigin = DataOrigin.REAL,
        schema_version: str = "1.0",
        created_at: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.schema_version = schema_version
        self.task_id = task_id
        self.provenance = provenance
        self.producer_module = producer_module
        self.data_origin = data_origin
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.data: Dict[str, Any] = data or {}

    def validate(self) -> bool:
        """Check that all required fields are present and non-empty.

        Returns:
            ``True`` if the contract is valid.

        Raises:
            ValueError: If any required field is missing or empty.
        """
        required_fields: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "producer_module": self.producer_module,
            "created_at": self.created_at,
        }
        for name, value in required_fields.items():
            if not value:
                raise ValueError(f"DataContract field '{name}' must not be empty")

        if not isinstance(self.data_origin, DataOrigin):
            raise ValueError(
                f"data_origin must be a DataOrigin enum, got {type(self.data_origin)}"
            )

        if not isinstance(self.provenance, Provenance):
            raise ValueError(
                f"provenance must be a Provenance instance, got {type(self.provenance)}"
            )

        if not self.provenance.module_chain:
            raise ValueError("provenance.module_chain must contain at least one module")

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the entire data contract to a plain dict."""
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "producer_module": self.producer_module,
            "created_at": self.created_at,
            "data_origin": self.data_origin.value,
            "provenance": self.provenance.to_dict(),
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataContract":
        """Reconstruct a ``DataContract`` from a plain dict."""
        prov_data = data.get("provenance", {})
        provenance = Provenance(
            source_files=prov_data.get("source_files", []),
            transformations=prov_data.get("transformations", []),
            timestamp=prov_data.get("timestamp", ""),
            module_chain=prov_data.get("module_chain", []),
        )
        origin_raw = data.get("data_origin", DataOrigin.REAL)
        if isinstance(origin_raw, str):
            origin_raw = DataOrigin(origin_raw)
        return cls(
            task_id=data["task_id"],
            producer_module=data["producer_module"],
            provenance=provenance,
            data_origin=origin_raw,
            schema_version=data.get("schema_version", "1.0"),
            created_at=data.get("created_at", ""),
            data=data.get("data", {}),
        )

    def is_real(self) -> bool:
        """Return ``True`` if this data has ``DataOrigin.REAL``."""
        return self.data_origin == DataOrigin.REAL

    def is_synthetic_or_mock(self) -> bool:
        """Return ``True`` if data is synthetic or mock (not for real claims)."""
        return self.data_origin in (DataOrigin.SYNTHETIC, DataOrigin.MOCK)
