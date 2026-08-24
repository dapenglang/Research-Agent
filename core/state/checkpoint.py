"""Checkpoint management for Research Agent v3.

Provides ``CheckpointManager`` which saves, loads, lists, and cleans up
per-module checkpoints.  Checkpoints are stored under
``state/<task_id>/checkpoints/<module_id>/``.

Each checkpoint consists of:
- ``checkpoint.json``  — the serialised data payload
- ``checkpoint.meta.json`` — metadata including timestamp and checksum
- ``checkpoint.checksum`` — SHA-256 of the data payload for integrity verification

Mid-experiment checkpoints are also supported via a ``is_experiment`` flag.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from Research_Agent_v3.core.exceptions import CheckpointError


class CheckpointManager:
    """Manage module-level checkpoints for a research task."""

    def __init__(self, state_root: str | Path = "state") -> None:
        self.state_root = Path(state_root)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _checkpoint_dir(self, task_id: str, module_id: str) -> Path:
        return self.state_root / task_id / "checkpoints" / module_id

    def _data_file(self, task_id: str, module_id: str) -> Path:
        return self._checkpoint_dir(task_id, module_id) / "checkpoint.json"

    def _meta_file(self, task_id: str, module_id: str) -> Path:
        return self._checkpoint_dir(task_id, module_id) / "checkpoint.meta.json"

    def _checksum_file(self, task_id: str, module_id: str) -> Path:
        return self._checkpoint_dir(task_id, module_id) / "checkpoint.checksum"

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def save_checkpoint(
        self,
        task_id: str,
        module_id: str,
        data: Dict[str, Any],
        is_experiment: bool = False,
    ) -> Path:
        """Save a checkpoint for the given module.

        Args:
            task_id: The parent research task ID.
            module_id: The module that produced this checkpoint.
            data: Arbitrary JSON-serialisable data to persist.
            is_experiment: If ``True``, marks this as a mid-experiment checkpoint.

        Returns:
            Path to the checkpoint directory.
        """
        ckpt_dir = self._checkpoint_dir(task_id, module_id)
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        data_file = self._data_file(task_id, module_id)
        meta_file = self._meta_file(task_id, module_id)
        checksum_file = self._checksum_file(task_id, module_id)

        # Serialise data
        data_json = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        data_file.write_text(data_json, encoding="utf-8")

        # Compute checksum
        checksum = hashlib.sha256(data_json.encode("utf-8")).hexdigest()
        checksum_file.write_text(checksum, encoding="utf-8")

        # Write metadata
        meta = {
            "task_id": task_id,
            "module_id": module_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_experiment": is_experiment,
            "checksum": checksum,
            "data_file": str(data_file),
        }
        meta_file.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return ckpt_dir

    def load_checkpoint(self, task_id: str, module_id: str) -> Dict[str, Any]:
        """Load and verify a checkpoint for the given module.

        Args:
            task_id: The parent research task ID.
            module_id: The module whose checkpoint to load.

        Returns:
            The deserialised checkpoint data.

        Raises:
            CheckpointError: If the checkpoint is missing or fails integrity
                verification.
        """
        data_file = self._data_file(task_id, module_id)
        meta_file = self._meta_file(task_id, module_id)
        checksum_file = self._checksum_file(task_id, module_id)

        if not data_file.exists():
            raise CheckpointError(
                f"Checkpoint not found for task={task_id}, module={module_id}"
            )

        data_json = data_file.read_text(encoding="utf-8")

        # Integrity verification
        if checksum_file.exists():
            expected_checksum = checksum_file.read_text(encoding="utf-8").strip()
            actual_checksum = hashlib.sha256(data_json.encode("utf-8")).hexdigest()
            if expected_checksum != actual_checksum:
                raise CheckpointError(
                    f"Checkpoint integrity verification failed for "
                    f"task={task_id}, module={module_id}: "
                    f"checksum mismatch (expected={expected_checksum}, "
                    f"actual={actual_checksum})"
                )

        data: Dict[str, Any] = json.loads(data_json)

        # Attach metadata if available
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            data["_checkpoint_meta"] = meta

        return data

    def list_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        """List all checkpoint metadata for a task.

        Args:
            task_id: The parent research task ID.

        Returns:
            A list of metadata dicts, one per checkpoint, sorted by timestamp.
        """
        ckpt_root = self.state_root / task_id / "checkpoints"
        if not ckpt_root.exists():
            return []

        results: List[Dict[str, Any]] = []
        for module_dir in sorted(ckpt_root.iterdir()):
            if not module_dir.is_dir():
                continue
            meta_file = module_dir / "checkpoint.meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                results.append(meta)
            else:
                # Checkpoint directory exists but no metadata — include basic info
                results.append({
                    "task_id": task_id,
                    "module_id": module_dir.name,
                    "timestamp": "",
                    "is_experiment": False,
                    "checksum": "",
                    "data_file": str(module_dir / "checkpoint.json"),
                })

        results.sort(key=lambda m: m.get("timestamp", ""))
        return results

    def cleanup_old_checkpoints(self, task_id: str, keep: int = 3) -> int:
        """Remove old checkpoint directories, keeping only the *keep* most recent.

        Args:
            task_id: The parent research task ID.
            keep: Maximum number of checkpoint directories to retain.

        Returns:
            Number of checkpoint directories removed.
        """
        ckpt_root = self.state_root / task_id / "checkpoints"
        if not ckpt_root.exists():
            return 0

        # Gather all checkpoint dirs with their timestamps
        entries: List[tuple[str, str]] = []
        for module_dir in ckpt_root.iterdir():
            if not module_dir.is_dir():
                continue
            meta_file = module_dir / "checkpoint.meta.json"
            timestamp = ""
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                timestamp = meta.get("timestamp", "")
            entries.append((module_dir.name, timestamp))

        # Sort by timestamp descending (newest first)
        entries.sort(key=lambda e: e[1], reverse=True)

        # Remove entries beyond *keep*
        to_remove = entries[keep:]
        removed = 0
        for module_id, _ in to_remove:
            module_dir = ckpt_root / module_id
            if module_dir.exists():
                shutil.rmtree(module_dir)
                removed += 1

        return removed

    def has_checkpoint(self, task_id: str, module_id: str) -> bool:
        """Return ``True`` if a checkpoint exists for the given module."""
        return self._data_file(task_id, module_id).exists()

    def verify_checkpoint(self, task_id: str, module_id: str) -> bool:
        """Verify the integrity of a checkpoint via its checksum.

        Returns:
            ``True`` if the checksum matches.

        Raises:
            CheckpointError: If the checkpoint is missing or corrupted.
        """
        data_file = self._data_file(task_id, module_id)
        checksum_file = self._checksum_file(task_id, module_id)

        if not data_file.exists():
            raise CheckpointError(
                f"Checkpoint not found for task={task_id}, module={module_id}"
            )

        if not checksum_file.exists():
            raise CheckpointError(
                f"Checksum file missing for task={task_id}, module={module_id}"
            )

        data_json = data_file.read_text(encoding="utf-8")
        expected = checksum_file.read_text(encoding="utf-8").strip()
        actual = hashlib.sha256(data_json.encode("utf-8")).hexdigest()

        if expected != actual:
            raise CheckpointError(
                f"Checkpoint corruption detected for task={task_id}, module={module_id}"
            )
        return True
