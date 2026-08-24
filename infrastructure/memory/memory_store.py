"""
Three-layer memory storage for Research Agent v3.

Layers:
  - universal:  Cross-domain, task-agnostic knowledge.
                Stored in: memory/universal/
  - domains:    Domain-specific knowledge (e.g. "vlm_safety").
                Stored in: memory/domains/<domain>/
  - projects:   Task-specific memory (scoped to a research task).
                Stored in: memory/projects/<task_id>/

Memory item schema:
  {
    "memory_id":    str,   # Unique identifier
    "type":         str,   # Item type (e.g. "fact", "hypothesis", "evidence")
    "content":      str,   # Main content text
    "evidence":     list,  # Supporting evidence references
    "created_at":   str,   # ISO 8601 timestamp
    "verified":     bool,  # Whether the item has been verified
    "domain":       str,   # Domain identifier (empty for universal)
    "task_id":      str,   # Task identifier (empty for non-project items)
  }

Storage format: individual JSON files per memory item.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Valid layer names
VALID_LAYERS: frozenset[str] = frozenset({"universal", "domains", "projects"})

# Required fields in a memory item
REQUIRED_FIELDS: frozenset[str] = frozenset({
    "memory_id", "type", "content", "created_at", "verified",
})


class MemoryStore:
    """
    Three-layer memory storage backed by JSON files.

    Usage:
        store = MemoryStore(data_root="/data/research_agent")
        store.store("universal", {
            "type": "fact",
            "content": "LLaVA uses CLIP-ViT as vision encoder",
            "domain": "vlm_safety",
        })
        items = store.retrieve("universal", {"type": "fact"})
    """

    def __init__(
        self,
        data_root: Optional[str] = None,
        memory_dir: Optional[str] = None,
    ) -> None:
        """
        Initialize the MemoryStore.

        Args:
            data_root:  Root data directory. If memory_dir is not given,
                        memory is stored under ``<data_root>/memory/``.
            memory_dir: Explicit memory directory path. Overrides data_root.
        """
        if memory_dir:
            self._memory_dir = Path(memory_dir)
        elif data_root:
            self._memory_dir = Path(data_root) / "memory"
        else:
            self._memory_dir = Path.cwd() / "memory"

        # Ensure base directories exist
        for layer in VALID_LAYERS:
            self._get_layer_dir(layer).mkdir(parents=True, exist_ok=True)

        logger.info("MemoryStore initialised, dir=%s", self._memory_dir)

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(self, layer: str, item: Dict[str, Any]) -> str:
        """
        Store a memory item in the specified layer.

        If the item does not have a ``memory_id``, one is generated.
        If it does not have a ``created_at`` timestamp, the current
        UTC time is used.

        Args:
            layer: One of "universal", "domains", "projects".
            item:  Memory item dict. Must contain at least "type" and
                   "content". May optionally include "domain", "task_id",
                   "evidence", "verified".

        Returns:
            The memory_id of the stored item.

        Raises:
            ValueError: If layer is invalid or item is missing required fields.
        """
        self._validate_layer(layer)

        # Ensure required fields with defaults
        item = dict(item)  # shallow copy
        if "memory_id" not in item:
            item["memory_id"] = self._generate_id()
        if "created_at" not in item:
            item["created_at"] = datetime.now(timezone.utc).isoformat()
        if "verified" not in item:
            item["verified"] = False
        if "evidence" not in item:
            item["evidence"] = []

        # Validate required fields
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            raise ValueError(f"Memory item missing required fields: {sorted(missing)}")

        if "type" not in item or not item["type"]:
            raise ValueError("Memory item must have a non-empty 'type' field")
        if "content" not in item or not item["content"]:
            raise ValueError("Memory item must have a non-empty 'content' field")

        # Determine storage path
        file_path = self._get_item_path(layer, item)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)

        logger.info(
            "Stored memory item %s in layer '%s' (type=%s)",
            item["memory_id"], layer, item["type"],
        )
        return item["memory_id"]

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(
        self,
        layer: str,
        query: Dict[str, Any],
        max_items: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memory items matching a query.

        The query is a dict of field-value pairs. An item matches if
        ALL specified fields match. String fields support substring
        matching (case-insensitive).

        Args:
            layer:     Memory layer to search.
            query:     Field-value pairs to match.
            max_items: Maximum number of items to return.

        Returns:
            List of matching memory item dicts, sorted by created_at
            (newest first).
        """
        self._validate_layer(layer)

        layer_dir = self._get_layer_dir(layer)
        items: List[Dict[str, Any]] = []

        # Walk all JSON files in the layer directory
        for json_file in layer_dir.rglob("*.json"):
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    item = json.load(f)
                if self._matches_query(item, query):
                    items.append(item)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read memory file %s: %s", json_file, e)

        # Sort by created_at (newest first), then limit
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        if len(items) > max_items:
            items = items[:max_items]

        logger.info(
            "Retrieved %d items from layer '%s' (query=%s, max=%d)",
            len(items), layer, query, max_items,
        )
        return items

    def retrieve_all(self, layer: str, max_items: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve all items from a layer (up to max_items)."""
        return self.retrieve(layer, {}, max_items=max_items)

    def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific memory item by its ID.

        Searches all layers.

        Args:
            memory_id: The memory item's unique identifier.

        Returns:
            The item dict, or None if not found.
        """
        for layer in VALID_LAYERS:
            layer_dir = self._get_layer_dir(layer)
            for json_file in layer_dir.rglob("*.json"):
                try:
                    with json_file.open("r", encoding="utf-8") as f:
                        item = json.load(f)
                    if item.get("memory_id") == memory_id:
                        return item
                except (json.JSONDecodeError, OSError):
                    continue
        return None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a memory item with new field values.

        Searches all layers for the item. If found, merges the updates
        into the existing item and rewrites the file.

        Args:
            item_id:  Memory item ID to update.
            updates:  Dict of field-value pairs to update.

        Returns:
            True if the item was found and updated, False otherwise.
        """
        for layer in VALID_LAYERS:
            layer_dir = self._get_layer_dir(layer)
            for json_file in layer_dir.rglob("*.json"):
                try:
                    with json_file.open("r", encoding="utf-8") as f:
                        item = json.load(f)
                    if item.get("memory_id") == item_id:
                        # Merge updates
                        item.update(updates)
                        with json_file.open("w", encoding="utf-8") as f:
                            json.dump(item, f, ensure_ascii=False, indent=2)
                        logger.info("Updated memory item %s", item_id)
                        return True
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to update %s: %s", json_file, e)
                    continue

        logger.warning("Memory item %s not found for update", item_id)
        return False

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, item_id: str) -> bool:
        """
        Delete a memory item by its ID.

        Searches all layers for the item.

        Args:
            item_id: Memory item ID to delete.

        Returns:
            True if the item was found and deleted, False otherwise.
        """
        for layer in VALID_LAYERS:
            layer_dir = self._get_layer_dir(layer)
            for json_file in layer_dir.rglob("*.json"):
                try:
                    with json_file.open("r", encoding="utf-8") as f:
                        item = json.load(f)
                    if item.get("memory_id") == item_id:
                        json_file.unlink()
                        logger.info("Deleted memory item %s", item_id)
                        return True
                except (json.JSONDecodeError, OSError):
                    continue

        logger.warning("Memory item %s not found for deletion", item_id)
        return False

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def count(self, layer: Optional[str] = None) -> int:
        """
        Count memory items in a layer (or all layers).

        Args:
            layer: Layer to count. If None, counts across all layers.

        Returns:
            Number of memory items.
        """
        layers = [layer] if layer else list(VALID_LAYERS)
        total = 0
        for l in layers:
            self._validate_layer(l)
            layer_dir = self._get_layer_dir(l)
            total += sum(1 for _ in layer_dir.rglob("*.json"))
        return total

    def get_stats(self) -> Dict[str, int]:
        """Return item counts per layer."""
        return {layer: self.count(layer) for layer in VALID_LAYERS}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_layer(self, layer: str) -> None:
        if layer not in VALID_LAYERS:
            raise ValueError(
                f"Invalid memory layer: '{layer}'. "
                f"Valid layers: {sorted(VALID_LAYERS)}"
            )

    def _get_layer_dir(self, layer: str) -> Path:
        """Get the directory path for a memory layer."""
        return self._memory_dir / layer

    def _get_item_path(self, layer: str, item: Dict[str, Any]) -> Path:
        """
        Determine the file path for a memory item.

        - universal:  memory/universal/<memory_id>.json
        - domains:    memory/domains/<domain>/<memory_id>.json
        - projects:   memory/projects/<task_id>/<memory_id>.json
        """
        memory_id = item["memory_id"]

        if layer == "universal":
            return self._memory_dir / "universal" / f"{memory_id}.json"
        elif layer == "domains":
            domain = item.get("domain", "default")
            return self._memory_dir / "domains" / domain / f"{memory_id}.json"
        elif layer == "projects":
            task_id = item.get("task_id", "default")
            return self._memory_dir / "projects" / task_id / f"{memory_id}.json"
        else:
            return self._memory_dir / layer / f"{memory_id}.json"

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique memory ID."""
        return f"mem_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _matches_query(item: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """
        Check if a memory item matches all query field-value pairs.

        String values use case-insensitive substring matching.
        Other types use equality.
        """
        for key, value in query.items():
            item_value = item.get(key)
            if item_value is None:
                return False
            if isinstance(value, str) and isinstance(item_value, str):
                if value.lower() not in item_value.lower():
                    return False
            elif isinstance(value, list) and isinstance(item_value, list):
                if not any(v in item_value for v in value):
                    return False
            elif item_value != value:
                return False
        return True
