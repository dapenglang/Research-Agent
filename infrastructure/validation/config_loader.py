"""
Configuration loader for Research Agent v3.

Load order (later files override earlier ones):
  1. machine.yaml        — Machine-specific paths and resources
  2. storage.yaml        — Storage paths and directories
  3. providers.yaml      — LLM provider configurations
  4. model_registry.yaml — Model configurations
  5. research_task.yaml  — Current research task definition

After loading, variable replacement (${DATA_ROOT}, etc.) is applied
to all path-like values.

Optional fields have default values so the system can run with
minimal configuration.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Files to load, in order (later overrides earlier)
CONFIG_FILES: List[str] = [
    "machine.yaml",
    "storage.yaml",
    "providers.yaml",
    "model_registry.yaml",
    "research_task.yaml",
]

# Default values for optional top-level configuration sections
DEFAULTS: Dict[str, Any] = {
    "machine": {
        "name": "default",
        "gpu": {"available": False, "vram_gb": 0.0, "device": "cpu"},
        "cpu": {"cores": 4},
        "ram_gb": 16.0,
    },
    "storage": {
        "paths": {
            "DATA_ROOT": "./data",
            "MODELS_DIR": "${DATA_ROOT}/models",
            "PAPERS_DIR": "${DATA_ROOT}/papers",
            "OUTPUTS_DIR": "${DATA_ROOT}/outputs",
        },
    },
    "providers": {
        "default": {
            "type": "mock",
            "model_name": "mock-llm",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
    },
    "models": {},
    "research_task": {
        "task_id": "default_task",
        "domain": "general",
        "description": "",
    },
}

# Pattern for ${VARIABLE} placeholders
_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


class ConfigLoader:
    """
    Loads and validates Research Agent v3 configuration files.

    Usage:
        loader = ConfigLoader()
        config = loader.load_all("/path/to/configs")
        errors = loader.validate(config)
        if errors:
            for e in errors:
                print(f"Config error: {e}")
    """

    def __init__(self) -> None:
        logger.debug("ConfigLoader initialised")

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self, config_dir: str) -> Dict[str, Any]:
        """
        Load all configuration files from a directory.

        Files are loaded in order: machine.yaml, storage.yaml,
        providers.yaml, model_registry.yaml, research_task.yaml.
        Later files override earlier ones for overlapping keys.

        After loading, ${VARIABLE} placeholders are resolved.

        Args:
            config_dir: Directory containing the YAML config files.

        Returns:
            Merged configuration dictionary.

        Raises:
            FileNotFoundError: If config_dir does not exist.
        """
        config_path = Path(config_dir)
        if not config_path.exists():
            raise FileNotFoundError(f"Config directory not found: {config_path}")

        # Start with defaults
        merged: Dict[str, Any] = self._deep_copy_defaults()

        # Load each config file in order
        for filename in CONFIG_FILES:
            file_path = config_path / filename
            if file_path.exists():
                try:
                    with file_path.open("r", encoding="utf-8") as f:
                        file_config = yaml.safe_load(f)
                    if file_config and isinstance(file_config, dict):
                        merged = self._deep_merge(merged, file_config)
                        logger.info("Loaded config: %s", filename)
                    elif file_config is None:
                        logger.debug("Config file is empty: %s", filename)
                except yaml.YAMLError as e:
                    logger.error("Failed to parse %s: %s", filename, e)
                    raise
                except OSError as e:
                    logger.error("Failed to read %s: %s", filename, e)
                    raise
            else:
                logger.debug("Config file not found (using defaults): %s", filename)

        # Apply variable replacement
        merged = self._resolve_variables(merged)

        # Store the config directory path for reference
        merged["_config_dir"] = str(config_path)

        logger.info("Configuration loaded from %s", config_path)
        return merged

    def load_single(self, file_path: str) -> Dict[str, Any]:
        """
        Load a single YAML config file.

        Args:
            file_path: Path to the YAML file.

        Returns:
            Parsed configuration dictionary.
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")

        with p.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config if isinstance(config, dict) else {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration dictionary.

        Checks for:
          - Required sections (machine, storage, providers)
          - Storage paths contain DATA_ROOT
          - Provider has a valid type
          - Research task has task_id and domain
          - Model configs have local_path

        Args:
            config: Configuration dictionary to validate.

        Returns:
            List of validation error strings (empty if valid).
        """
        errors: List[str] = []

        # Check required sections
        for section in ("machine", "storage", "providers"):
            if section not in config:
                errors.append(f"Missing required section: '{section}'")

        # Validate storage
        storage = config.get("storage", {})
        paths = storage.get("paths", {})
        if not paths:
            errors.append("Storage section missing 'paths' mapping")
        elif "DATA_ROOT" not in paths:
            errors.append("Storage paths must include 'DATA_ROOT'")

        # Validate providers
        providers = config.get("providers", {})
        default_provider = providers.get("default", {})
        if not default_provider:
            errors.append("Providers section missing 'default' provider")
        else:
            provider_type = default_provider.get("type", "")
            if provider_type not in ("openai", "local", "mock", "none"):
                errors.append(
                    f"Invalid provider type: '{provider_type}'. "
                    f"Must be one of: openai, local, mock, none"
                )
            if provider_type == "openai" and not default_provider.get("api_key"):
                # API key may come from env var
                if not os.environ.get("OPENAI_API_KEY"):
                    errors.append(
                        "OpenAI provider configured but no api_key in config "
                        "and OPENAI_API_KEY env var is not set"
                    )
            if provider_type == "local" and not default_provider.get("endpoint"):
                if not os.environ.get("LOCAL_LLM_ENDPOINT"):
                    errors.append(
                        "Local provider configured but no endpoint in config "
                        "and LOCAL_LLM_ENDPOINT env var is not set"
                    )

        # Validate models
        models = config.get("models", {})
        for model_name, model_config in models.items():
            if not isinstance(model_config, dict):
                errors.append(f"Model '{model_name}' config must be a mapping")
                continue
            if "local_path" not in model_config and not model_config.get("auto_download", {}).get("enabled"):
                errors.append(
                    f"Model '{model_name}' has no 'local_path' and "
                    f"auto_download is not enabled"
                )

        # Validate research task
        task = config.get("research_task", {})
        if task:
            if "task_id" not in task or not task["task_id"]:
                errors.append("Research task must have a non-empty 'task_id'")
            if "domain" not in task or not task["domain"]:
                errors.append("Research task must have a non-empty 'domain'")

        # Validate nested research content (formal template)
        research = config.get("research", {})
        if research:
            if not research.get("domain"):
                errors.append("research.domain must be non-empty when 'research' section is present")
            if not research.get("keywords"):
                errors.append("research.keywords must be non-empty when 'research' section is present")
            if not research.get("research_question"):
                errors.append("research.research_question must be non-empty when 'research' section is present")
        elif config.get("task_id") and not config.get("keywords"):
            # No research section and no flat keywords — warn (E2E tests may skip this)
            logger.warning(
                "research_task config has no 'research' section and no top-level "
                "'keywords'; formal research tasks should use the nested format. "
                "See configs/research_task_template.yaml"
            )

        # Validate machine
        machine = config.get("machine", {})
        if machine:
            gpu = machine.get("gpu", {})
            if gpu.get("available", False) and gpu.get("vram_gb", 0) <= 0:
                errors.append("GPU is marked as available but vram_gb is 0 or missing")

        if errors:
            logger.warning("Configuration validation found %d error(s)", len(errors))
        else:
            logger.info("Configuration validation passed")

        return errors

    # ------------------------------------------------------------------
    # Variable replacement
    # ------------------------------------------------------------------

    def resolve_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve ${VARIABLE} placeholders in all string values.

        Variables are looked up from the storage.paths section.

        Args:
            config: Configuration dictionary.

        Returns:
            New dictionary with all resolvable variables replaced.
        """
        return self._resolve_variables(config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deep_copy_defaults() -> Dict[str, Any]:
        """Create a deep copy of the DEFAULTS dict."""
        import copy
        return copy.deepcopy(DEFAULTS)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge *overlay* into *base*.

        - Dict values are merged recursively.
        - Non-dict values from overlay replace base values.
        - Base is not modified; a new dict is returned.
        """
        result = dict(base)
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _resolve_variables(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve ${VARIABLE} placeholders throughout the config.

        Uses storage.paths as the variable source. Variables can
        reference each other (e.g. MODELS_DIR references DATA_ROOT).
        """
        # Extract variables from storage.paths
        paths = config.get("storage", {}).get("paths", {})
        variables: Dict[str, str] = {}
        for k, v in paths.items():
            if isinstance(v, str):
                variables[k] = v

        # Resolve internal references (MODELS_DIR -> ${DATA_ROOT}/models -> /actual/path/models)
        max_iterations = 10
        for _ in range(max_iterations):
            changed = False
            for key, value in list(variables.items()):
                if _VAR_PATTERN.search(value):
                    resolved = ConfigLoader._substitute(value, variables)
                    if resolved != value:
                        variables[key] = resolved
                        changed = True
            if not changed:
                break

        # Now resolve all string values in the config
        return ConfigLoader._resolve_in_dict(config, variables)

    @staticmethod
    def _resolve_in_dict(obj: Any, variables: Dict[str, str]) -> Any:
        """Recursively resolve variables in a dict/list/str structure."""
        if isinstance(obj, str):
            return ConfigLoader._substitute(obj, variables)
        elif isinstance(obj, dict):
            return {k: ConfigLoader._resolve_in_dict(v, variables) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ConfigLoader._resolve_in_dict(item, variables) for item in obj]
        else:
            return obj

    @staticmethod
    def _substitute(text: str, variables: Dict[str, str]) -> str:
        """Replace ${VARIABLE} placeholders in a string."""

        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))

        return _VAR_PATTERN.sub(_replace, text)
