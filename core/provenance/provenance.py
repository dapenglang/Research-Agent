"""Provenance tracking for Research Agent v3.

Tracks the full chain of data transformations from source paper through
analysis, method design, experiment, results, figures, and paper claims.

The tracker prevents dangerous confusions:
- Synthetic data being mistaken for real experimental results.
- Mock data being used in final claims.
- LLM guesses being presented as verified facts.

Each data item is assigned an origin type, and the tracker enforces rules
about which origins can flow into which downstream consumers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from Research_Agent_v3.core.exceptions import ProvenanceError


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProvenanceEntry:
    """A single entry in the provenance chain of a data item."""

    data_id: str
    origin_type: str  # real, synthetic, mock, external, manual, llm_generated
    source: str  # description or path of the source
    module_id: str  # which module produced this data
    timestamp: str = ""
    parent_ids: List[str] = field(default_factory=list)
    transformation: str = ""
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def compute_checksum(self) -> str:
        """Compute a deterministic checksum of this entry (excluding the checksum field)."""
        data = self.to_dict()
        data.pop("checksum", None)
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------
# Origin compatibility rules
# -----------------------------------------------------------------------

# An origin type can only be consumed by modules that accept it.
# This prevents synthetic/mock/llm data from flowing into modules
# that produce final real claims.
_ORIGIN_CONSUMPTION_RULES: Dict[str, Set[str]] = {
    # Real data can flow anywhere
    "real": {
        "literature_analysis",
        "innovation_generation",
        "method_design",
        "experiment_planning",
        "experiment_execution",
        "result_analysis",
        "figure_table",
        "paper_writing",
    },
    # Synthetic data is only for development and experiment engine
    "synthetic": {
        "experiment_planning",
        "experiment_execution",
        "result_analysis",
    },
    # Mock data is only for testing
    "mock": {
        "experiment_planning",
        "experiment_execution",
    },
    # External data (e.g. downloaded datasets) can flow to analysis
    "external": {
        "literature_analysis",
        "experiment_planning",
        "experiment_execution",
        "result_analysis",
    },
    # Manual input (e.g. user-provided config) can flow to planning
    "manual": {
        "experiment_planning",
        "method_design",
        "paper_writing",
    },
    # LLM-generated content must be flagged and cannot be used as factual
    "llm_generated": {
        "innovation_generation",
        "paper_writing",
    },
}

# Origins that must NOT appear in final paper claims
_NON_CLAIM_ORIGINS: Set[str] = {"synthetic", "mock", "llm_generated"}


class ProvenanceTracker:
    """Tracks provenance chains for all data items in the research pipeline.

    The tracker maintains an in-memory graph of data_id -> ProvenanceEntry
    and can persist/load from a JSON file.
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        """
        Args:
            storage_path: If provided, the tracker will load from and save to
                this JSON file.
        """
        self._entries: Dict[str, ProvenanceEntry] = {}
        self._storage_path = storage_path
        if storage_path:
            self._load()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def record_origin(
        self,
        data_id: str,
        origin_type: str,
        source: str,
        module_id: str,
        parent_ids: Optional[List[str]] = None,
        transformation: str = "",
    ) -> ProvenanceEntry:
        """Record the origin of a data item.

        Args:
            data_id: Unique identifier for the data item.
            origin_type: One of ``real``, ``synthetic``, ``mock``, ``external``,
                ``manual``, ``llm_generated``.
            source: Description or path of the original source.
            module_id: ID of the module that produced this data.
            parent_ids: IDs of parent data items this was derived from.
            transformation: Description of the transformation applied.

        Returns:
            The created :class:`ProvenanceEntry`.

        Raises:
            ProvenanceError: If *origin_type* is not recognised or if a
                parent ID is not registered.
        """
        valid_origins = set(_ORIGIN_CONSUMPTION_RULES.keys())
        if origin_type not in valid_origins:
            raise ProvenanceError(
                f"Unknown origin_type '{origin_type}'. "
                f"Valid types: {sorted(valid_origins)}"
            )

        parent_ids = parent_ids or []
        for pid in parent_ids:
            if pid not in self._entries:
                raise ProvenanceError(
                    f"Parent data_id '{pid}' not found in provenance tracker"
                )

        # If this data_id already exists, we are updating it
        entry = ProvenanceEntry(
            data_id=data_id,
            origin_type=origin_type,
            source=source,
            module_id=module_id,
            parent_ids=parent_ids,
            transformation=transformation,
        )
        entry.checksum = entry.compute_checksum()
        self._entries[data_id] = entry
        self._save()
        return entry

    def get_chain(self, data_id: str) -> List[ProvenanceEntry]:
        """Get the full provenance chain for a data item (root -> leaf).

        Args:
            data_id: The data item to trace.

        Returns:
            Ordered list of entries from the earliest ancestor to the item
            itself.

        Raises:
            ProvenanceError: If *data_id* is not registered.
        """
        if data_id not in self._entries:
            raise ProvenanceError(f"Data ID '{data_id}' not found in provenance tracker")

        chain: List[ProvenanceEntry] = []
        visited: Set[str] = set()

        def _walk(did: str) -> None:
            if did in visited:
                return
            visited.add(did)
            entry = self._entries[did]
            for pid in entry.parent_ids:
                _walk(pid)
            chain.append(entry)

        _walk(data_id)
        return chain

    def verify_integrity(self, data_id: str) -> bool:
        """Verify the integrity of a data item's provenance chain.

        Checks:
        1. All parent IDs exist in the tracker.
        2. All checksums are valid (no tampering).
        3. No synthetic/mock/llm data flows into a module that requires real data.

        Args:
            data_id: The data item to verify.

        Returns:
            ``True`` if the chain is intact and valid.

        Raises:
            ProvenanceError: If any integrity check fails.
        """
        if data_id not in self._entries:
            raise ProvenanceError(f"Data ID '{data_id}' not found in provenance tracker")

        chain = self.get_chain(data_id)

        for entry in chain:
            # Check parent IDs exist
            for pid in entry.parent_ids:
                if pid not in self._entries:
                    raise ProvenanceError(
                        f"Broken chain: parent '{pid}' of '{entry.data_id}' is missing"
                    )

            # Verify checksum
            expected = entry.compute_checksum()
            if entry.checksum != expected:
                raise ProvenanceError(
                    f"Checksum mismatch for '{entry.data_id}': "
                    f"expected={expected}, stored={entry.checksum}. "
                    "Entry may have been tampered with."
                )

            # Check origin compatibility: the origin of this entry must be
            # consumable by the module that produced it.
            allowed_modules = _ORIGIN_CONSUMPTION_RULES.get(entry.origin_type, set())
            if entry.module_id not in allowed_modules:
                # Special case: the first entry (no parents) is the origin
                # declaration itself, which is always valid.
                if entry.parent_ids:
                    raise ProvenanceError(
                        f"Origin violation: data '{entry.data_id}' has origin "
                        f"'{entry.origin_type}' but was produced by module "
                        f"'{entry.module_id}' which does not accept that origin. "
                        f"Allowed modules: {sorted(allowed_modules)}"
                    )

        return True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_origin_type(self, data_id: str) -> str:
        """Return the origin type of a data item."""
        if data_id not in self._entries:
            raise ProvenanceError(f"Data ID '{data_id}' not found")
        return self._entries[data_id].origin_type

    def is_real(self, data_id: str) -> bool:
        """Return ``True`` if the data item (and all ancestors) have real origin."""
        chain = self.get_chain(data_id)
        return all(e.origin_type == "real" for e in chain)

    def is_claim_safe(self, data_id: str) -> bool:
        """Return ``True`` if this data item is safe to use in final paper claims.

        Data with synthetic, mock, or llm_generated origins anywhere in its
        chain is NOT claim-safe.
        """
        chain = self.get_chain(data_id)
        return not any(e.origin_type in _NON_CLAIM_ORIGINS for e in chain)

    def get_all_entries(self) -> Dict[str, ProvenanceEntry]:
        """Return all tracked entries as a dict (data_id -> entry)."""
        return dict(self._entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Save all entries to the storage file if configured."""
        if not self._storage_path:
            return
        from pathlib import Path

        data = {
            did: entry.to_dict() for did, entry in self._entries.items()
        }
        p = Path(self._storage_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        """Load entries from the storage file if it exists."""
        from pathlib import Path

        p = Path(self._storage_path)  # type: ignore[arg-type]
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        for did, entry_data in data.items():
            entry = ProvenanceEntry(
                data_id=entry_data["data_id"],
                origin_type=entry_data["origin_type"],
                source=entry_data["source"],
                module_id=entry_data["module_id"],
                timestamp=entry_data.get("timestamp", ""),
                parent_ids=entry_data.get("parent_ids", []),
                transformation=entry_data.get("transformation", ""),
                checksum=entry_data.get("checksum", ""),
            )
            self._entries[did] = entry
