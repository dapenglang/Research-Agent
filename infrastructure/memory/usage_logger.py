"""
Memory usage logging for Research Agent v3.

Logs every memory retrieval event as a JSONL entry in
``memory/usage_log.jsonl``. Each entry records:
  - memory_id:            The retrieved memory item's ID
  - source_task:          The task that triggered retrieval
  - source_domain:        The domain context of the retrieval
  - relevance_score:      Computed relevance score (0.0–1.0)
  - retrieval_reason:     Why this memory was retrieved
  - injected_to_module:   Which module received the memory
  - impact_on_decision:   How the memory affected the module's output
  - timestamp:            ISO 8601 UTC timestamp

The log enables auditing of memory usage patterns and tracing
which memories influenced which research decisions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UsageLogger:
    """
    Logs memory retrieval events to a JSONL file.

    Usage:
        usage_logger = UsageLogger(data_root="/data/research_agent")
        usage_logger.log(
            memory_id="mem_abc123",
            source_task="task_001",
            source_domain="vlm_safety",
            relevance_score=0.85,
            retrieval_reason="keyword match on 'cross-modal safety'",
            injected_to_module="05_innovation_reasoning",
            impact_on_decision="suggested UniSafe framework direction",
        )
    """

    def __init__(
        self,
        data_root: Optional[str] = None,
        memory_dir: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> None:
        """
        Initialize the UsageLogger.

        Args:
            data_root:  Root data directory. If log_file is not given,
                        the log is stored at ``<data_root>/memory/usage_log.jsonl``.
            memory_dir: Explicit memory directory path.
            log_file:   Explicit path to the JSONL log file.
        """
        if log_file:
            self._log_file = Path(log_file)
        elif memory_dir:
            self._log_file = Path(memory_dir) / "usage_log.jsonl"
        elif data_root:
            self._log_file = Path(data_root) / "memory" / "usage_log.jsonl"
        else:
            self._log_file = Path.cwd() / "memory" / "usage_log.jsonl"

        # Ensure parent directory exists
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("UsageLogger initialised, log_file=%s", self._log_file)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(
        self,
        memory_id: str,
        source_task: str,
        source_domain: str,
        relevance_score: float,
        retrieval_reason: str,
        injected_to_module: str,
        impact_on_decision: str,
    ) -> None:
        """
        Log a single memory retrieval event.

        Args:
            memory_id:           The retrieved memory item's ID.
            source_task:         The task that triggered the retrieval.
            source_domain:       The domain context.
            relevance_score:     Relevance score (0.0–1.0).
            retrieval_reason:    Why this memory was retrieved.
            injected_to_module:  Which module received the memory.
            impact_on_decision:  How the memory affected the output.
        """
        entry: Dict[str, Any] = {
            "memory_id": memory_id,
            "source_task": source_task,
            "source_domain": source_domain,
            "relevance_score": round(float(relevance_score), 4),
            "retrieval_reason": retrieval_reason,
            "injected_to_module": injected_to_module,
            "impact_on_decision": impact_on_decision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Append to JSONL file
        with self._log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.debug(
            "Logged usage: memory_id=%s, module=%s, score=%.3f",
            memory_id, injected_to_module, relevance_score,
        )

    def log_batch(self, entries: List[Dict[str, Any]]) -> None:
        """
        Log multiple memory retrieval events at once.

        Args:
            entries: List of dicts, each with the same keys as the
                     parameters of :meth:`log`.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._log_file.open("a", encoding="utf-8") as f:
            for entry in entries:
                record = {
                    "memory_id": entry.get("memory_id", ""),
                    "source_task": entry.get("source_task", ""),
                    "source_domain": entry.get("source_domain", ""),
                    "relevance_score": round(float(entry.get("relevance_score", 0.0)), 4),
                    "retrieval_reason": entry.get("retrieval_reason", ""),
                    "injected_to_module": entry.get("injected_to_module", ""),
                    "impact_on_decision": entry.get("impact_on_decision", ""),
                    "timestamp": entry.get("timestamp", timestamp),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info("Logged %d usage entries in batch", len(entries))

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def read_all(self) -> List[Dict[str, Any]]:
        """
        Read all log entries from the JSONL file.

        Returns:
            List of log entry dicts, in file order (oldest first).
        """
        if not self._log_file.exists():
            return []

        entries: List[Dict[str, Any]] = []
        with self._log_file.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON at line %d: %s", line_num, e)

        return entries

    def read_by_memory(self, memory_id: str) -> List[Dict[str, Any]]:
        """Read all log entries for a specific memory item."""
        return [e for e in self.read_all() if e.get("memory_id") == memory_id]

    def read_by_module(self, module_id: str) -> List[Dict[str, Any]]:
        """Read all log entries for a specific module."""
        return [e for e in self.read_all() if e.get("injected_to_module") == module_id]

    def read_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Read all log entries for a specific task."""
        return [e for e in self.read_all() if e.get("source_task") == task_id]

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the total number of log entries."""
        if not self._log_file.exists():
            return 0
        count = 0
        with self._log_file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def clear(self) -> None:
        """Delete all log entries (truncate the file)."""
        self._log_file.write_text("", encoding="utf-8")
        logger.info("Cleared usage log: %s", self._log_file)

    def get_log_file(self) -> Path:
        """Return the path to the JSONL log file."""
        return self._log_file

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Compute basic statistics from the usage log.

        Returns:
            Dict with keys:
              - total_entries: Total number of log entries
              - unique_memories: Number of distinct memory_ids
              - unique_modules: Number of distinct modules
              - avg_relevance: Average relevance score
              - by_module: Dict mapping module_id to entry count
        """
        entries = self.read_all()
        if not entries:
            return {
                "total_entries": 0,
                "unique_memories": 0,
                "unique_modules": 0,
                "avg_relevance": 0.0,
                "by_module": {},
            }

        memory_ids = set()
        module_ids: Dict[str, int] = {}
        total_score = 0.0

        for entry in entries:
            memory_ids.add(entry.get("memory_id", ""))
            module = entry.get("injected_to_module", "")
            module_ids[module] = module_ids.get(module, 0) + 1
            total_score += float(entry.get("relevance_score", 0.0))

        return {
            "total_entries": len(entries),
            "unique_memories": len(memory_ids),
            "unique_modules": len(module_ids),
            "avg_relevance": round(total_score / len(entries), 4),
            "by_module": module_ids,
        }
