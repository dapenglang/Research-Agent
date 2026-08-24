"""
Path resolution with variable replacement.

Supports the following variables in path strings:
  ${DATA_ROOT}     — Root data directory for the project
  ${TASK_ID}       — Current research task identifier
  ${MODULE_ID}     — Current module identifier
  ${PAPER_ID}      — Paper identifier
  ${MODEL_NAME}    — Model name
  ${MODELS_DIR}    — Directory for stored models
  ${PAPERS_DIR}    — Directory for stored papers
  ${OUTPUTS_DIR}   — Directory for outputs

All paths use pathlib.Path for cross-OS compatibility.
Directories are auto-created on first use.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

# Regex pattern for ${VARIABLE_NAME} style placeholders
_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

# All supported variable names
SUPPORTED_VARIABLES = frozenset({
    "DATA_ROOT",
    "TASK_ID",
    "MODULE_ID",
    "PAPER_ID",
    "MODEL_NAME",
    "MODELS_DIR",
    "PAPERS_DIR",
    "OUTPUTS_DIR",
})


class PathResolver:
    """
    Resolves path strings containing ${VARIABLE} placeholders into
    concrete pathlib.Path objects.

    Usage:
        resolver = PathResolver({
            "DATA_ROOT": "/data/research_agent",
            "MODELS_DIR": "${DATA_ROOT}/models",
        })
        path = resolver.resolve("${MODELS_DIR}/llava-1.5-7b")
        # -> Path("/data/research_agent/models/llava-1.5-7b")

    Variables can reference other variables (e.g. MODELS_DIR references
    DATA_ROOT). Resolution is recursive: the resolver keeps substituting
    until no ${...} placeholders remain or no matching variable is found.
    """

    def __init__(self, variables: Dict[str, str] | None = None) -> None:
        """
        Initialize the resolver with a set of named variables.

        Args:
            variables: Mapping of variable name (without ${}) to value.
                       Values may themselves contain ${...} references.
        """
        self._variables: Dict[str, str] = dict(variables) if variables else {}
        # Pre-resolve internal references so that MODELS_DIR -> absolute
        self._resolve_internal_references()
        logger.debug("PathResolver initialised with %d variables", len(self._variables))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, path: str, context: Dict[str, str] | None = None) -> Path:
        """
        Resolve a path string by replacing all ${VARIABLE} placeholders.

        Context variables override the resolver's default variables for
        this call only (they are not stored permanently).

        Args:
            path:   Path string with optional ${VARIABLE} placeholders.
            context: Optional per-call variable overrides.

        Returns:
            A resolved pathlib.Path object. If the path is relative after
            variable substitution it is resolved against the current
            working directory.

        Raises:
            KeyError: If a ${VARIABLE} is used that cannot be resolved
                      from either the context or the resolver's defaults.
        """
        merged: Dict[str, str] = dict(self._variables)
        if context:
            merged.update(context)

        resolved_str = self._substitute(path, merged)

        # Convert to Path and expand user (~) for cross-OS support
        result = Path(resolved_str).expanduser()

        logger.debug("Resolved path: '%s' -> '%s'", path, result)
        return result

    def resolve_many(
        self, paths: list[str], context: Dict[str, str] | None = None
    ) -> list[Path]:
        """Resolve a list of path strings."""
        return [self.resolve(p, context) for p in paths]

    def ensure_dir(self, path: Path) -> Path:
        """
        Ensure a directory exists, creating it (and parents) if needed.

        Args:
            path: Directory path to create.

        Returns:
            The same Path object (now guaranteed to exist).
        """
        path.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured directory exists: %s", path)
        return path

    def resolve_and_ensure(self, path: str, context: Dict[str, str] | None = None) -> Path:
        """
        Resolve a path string and ensure its parent directory exists.

        Useful for file paths where the file itself may not exist yet
        but the containing directory must.
        """
        resolved = self.resolve(path, context)
        if resolved.parent and not resolved.parent.exists():
            self.ensure_dir(resolved.parent)
        return resolved

    def get_variables(self) -> Dict[str, str]:
        """Return a copy of the currently configured variables."""
        return dict(self._variables)

    def set_variable(self, name: str, value: str) -> None:
        """
        Set or update a single variable.

        Args:
            name:  Variable name (without ${}).
            value: Variable value (may contain ${...} references).
        """
        self._variables[name] = value
        self._resolve_internal_references()

    @staticmethod
    def load_storage_config(config_path: str) -> Dict[str, Any]:
        """
        Load a storage configuration YAML file.

        The YAML file should contain a top-level ``paths`` mapping with
        variable definitions. Example::

            paths:
              DATA_ROOT: /data/research_agent
              MODELS_DIR: ${DATA_ROOT}/models
              PAPERS_DIR: ${DATA_ROOT}/papers
              OUTPUTS_DIR: ${DATA_ROOT}/outputs

        Args:
            config_path: Path to the YAML config file.

        Returns:
            Dictionary with the parsed configuration.

        Raises:
            FileNotFoundError: If the config file does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        p = Path(config_path)
        if not p.exists():
            raise FileNotFoundError(f"Storage config file not found: {p}")

        with p.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if config is None:
            config = {}

        if not isinstance(config, dict):
            raise ValueError(
                f"Storage config must be a mapping, got {type(config).__name__}"
            )

        logger.info("Loaded storage config from %s (%d keys)", p, len(config))
        return config

    @classmethod
    def from_config_file(cls, config_path: str) -> "PathResolver":
        """
        Create a PathResolver from a storage configuration YAML file.

        Args:
            config_path: Path to the YAML config file.

        Returns:
            A configured PathResolver instance.
        """
        config = cls.load_storage_config(config_path)
        paths = config.get("paths", config)
        return cls(paths if isinstance(paths, dict) else {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_internal_references(self) -> None:
        """Resolve variables that reference other variables."""
        max_iterations = 10
        for _ in range(max_iterations):
            changed = False
            for key, value in list(self._variables.items()):
                if _VAR_PATTERN.search(value):
                    resolved = self._substitute(value, self._variables)
                    if resolved != value:
                        self._variables[key] = resolved
                        changed = True
            if not changed:
                break

    @staticmethod
    def _substitute(text: str, variables: Dict[str, str]) -> str:
        """
        Replace all ${VARIABLE} placeholders in *text* using *variables*.

        Args:
            text:       String potentially containing ${...} placeholders.
            variables:  Mapping of variable name to value.

        Returns:
            String with all resolvable placeholders replaced.

        Raises:
            KeyError: If a placeholder variable is not found.
        """

        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name in variables:
                return variables[var_name]
            raise KeyError(
                f"Unresolved path variable: '${{{var_name}}}'. "
                f"Available variables: {sorted(variables.keys())}"
            )

        return _VAR_PATTERN.sub(_replace, text)
