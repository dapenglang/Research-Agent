"""
Storage management for Research Agent v3.

Provides disk-space checking and category-based path resolution for:
  models, datasets, papers, experiments, external_data, cache, memory, outputs

Disk space is checked before large operations (model downloads, dataset
caching, experiment output) to prevent failures due to insufficient space.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, Optional

from Research_Agent_v3.infrastructure.storage.path_resolver import PathResolver

logger = logging.getLogger(__name__)

# Supported storage categories and their sub-directory names under DATA_ROOT
CATEGORIES: Dict[str, str] = {
    "models": "models",
    "datasets": "datasets",
    "papers": "papers",
    "experiments": "experiments",
    "external_data": "external_data",
    "cache": "cache",
    "memory": "memory",
    "outputs": "outputs",
}

# Minimum free disk space (GB) required for various operations
DEFAULT_MIN_FREE_GB: float = 5.0


class StorageManager:
    """
    Manages storage paths and disk-space for the Research Agent.

    Wraps a :class:`PathResolver` for variable substitution and adds:
      - Category-based path resolution (models, papers, outputs, etc.)
      - Directory creation and validation
      - Disk-space checking before large operations

    Usage:
        sm = StorageManager(data_root="/data/research_agent")
        model_path = sm.get_path("models", "llava-1.5-7b")
        # -> Path("/data/research_agent/models/llava-1.5-7b")

        if sm.check_disk_space(required_gb=20.0):
            # proceed with model download
            ...
    """

    def __init__(
        self,
        data_root: Optional[str] = None,
        resolver: Optional[PathResolver] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize the StorageManager.

        Exactly one of *data_root* or *resolver* should typically be
        provided. If *resolver* is given, it is used directly. Otherwise
        a new PathResolver is created with DATA_ROOT set to *data_root*
        (or the current working directory if data_root is None).

        Args:
            data_root: Root data directory path.
            resolver:  Pre-configured PathResolver to use.
            variables: Additional path variables (merged with data_root).
        """
        if resolver is not None:
            self._resolver = resolver
        else:
            root = data_root or str(Path.cwd())
            vars_dict: Dict[str, str] = {"DATA_ROOT": root}
            if variables:
                vars_dict.update(variables)
            # Derive category dirs from DATA_ROOT
            for cat, subdir in CATEGORIES.items():
                var_name = f"{cat.upper()}_DIR"
                vars_dict.setdefault(var_name, f"${{DATA_ROOT}}/{subdir}")
            self._resolver = PathResolver(vars_dict)

        logger.info(
            "StorageManager initialised, DATA_ROOT=%s",
            self._resolver.get_variables().get("DATA_ROOT", "?"),
        )

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def get_path(self, category: str, *args: str) -> Path:
        """
        Resolve a path within a storage category.

        Args:
            category: One of: models, datasets, papers, experiments,
                      external_data, cache, memory, outputs.
            *args:    Additional path components (subdirectories, filenames).

        Returns:
            Resolved Path object. The parent directory is auto-created.

        Raises:
            ValueError: If *category* is not a recognised storage category.
        """
        if category not in CATEGORIES:
            raise ValueError(
                f"Unknown storage category: '{category}'. "
                f"Valid categories: {sorted(CATEGORIES.keys())}"
            )

        var_name = f"{category.upper()}_DIR"
        base = self._resolver.resolve(f"${{{var_name}}}")

        path = base.joinpath(*args) if args else base
        return path

    def get_resolver(self) -> PathResolver:
        """Return the underlying PathResolver."""
        return self._resolver

    def get_data_root(self) -> Path:
        """Return the DATA_ROOT path."""
        return self._resolver.resolve("${DATA_ROOT}")

    # ------------------------------------------------------------------
    # Directory management
    # ------------------------------------------------------------------

    def ensure_dir(self, path: Path) -> Path:
        """
        Ensure a directory exists, creating it (and parents) if needed.

        Args:
            path: Directory path to create.

        Returns:
            The same Path object.
        """
        path.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured directory: %s", path)
        return path

    def ensure_category_dir(self, category: str) -> Path:
        """
        Ensure the root directory for a storage category exists.

        Args:
            category: Storage category name.

        Returns:
            Path to the category directory.
        """
        path = self.get_path(category)
        return self.ensure_dir(path)

    def ensure_all_dirs(self) -> None:
        """Create all category directories if they don't exist."""
        for category in CATEGORIES:
            self.ensure_category_dir(category)
        logger.info("All storage directories ensured under %s", self.get_data_root())

    # ------------------------------------------------------------------
    # Disk-space checking
    # ------------------------------------------------------------------

    def check_disk_space(self, required_gb: float = DEFAULT_MIN_FREE_GB) -> bool:
        """
        Check if sufficient free disk space is available.

        Uses :func:`shutil.disk_usage` which works on Windows, Linux,
        and macOS.

        Args:
            required_gb: Minimum free space required in gigabytes.

        Returns:
            True if the available free space is >= required_gb, False otherwise.
        """
        info = self.get_disk_info()
        free_gb = info["free_gb"]
        ok = free_gb >= required_gb
        if ok:
            logger.debug(
                "Disk space OK: %.1f GB free (required %.1f GB)",
                free_gb, required_gb,
            )
        else:
            logger.warning(
                "Insufficient disk space: %.1f GB free, %.1f GB required",
                free_gb, required_gb,
            )
        return ok

    def get_disk_info(self) -> Dict[str, float]:
        """
        Get disk usage information for the DATA_ROOT volume.

        Returns:
            Dictionary with keys:
              - total_gb:  Total disk capacity in GB.
              - used_gb:   Used disk space in GB.
              - free_gb:   Free disk space in GB.
              - percent:   Percentage of disk used (0.0–100.0).
        """
        data_root = self.get_data_root()
        # If data_root doesn't exist yet, check the parent that does
        check_path = data_root
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent

        usage = shutil.disk_usage(str(check_path))

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        percent = (usage.used / usage.total * 100.0) if usage.total > 0 else 0.0

        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent": round(percent, 2),
        }

    def get_category_size(self, category: str) -> float:
        """
        Calculate the total size of a storage category in GB.

        Args:
            category: Storage category name.

        Returns:
            Size in GB (0.0 if directory doesn't exist).
        """
        path = self.get_path(category)
        if not path.exists():
            return 0.0

        total_bytes = 0
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total_bytes += f.stat().st_size
                except OSError:
                    pass

        return round(total_bytes / (1024 ** 3), 2)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"StorageManager(data_root={self.get_data_root()})"
