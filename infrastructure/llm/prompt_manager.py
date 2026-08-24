"""
Prompt template management for Research Agent v3.

Loads, caches, and renders prompt templates from files in
``infrastructure/llm/templates/``. If a template file is not found,
a basic fallback template is returned.

Template files use ``{VARIABLE_NAME}`` placeholders that are replaced
at render time via ``str.format_map``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Directory where template files live (relative to this module)
_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Regex to find {VARIABLE_NAME} style placeholders
_PLACEHOLDER_RE = re.compile(r"\{([A-Z_][A-Z0-9_]*)\}")


# Built-in fallback templates used when no file is found
_FALLBACK_TEMPLATES: Dict[str, str] = {
    "gap_analysis": (
        "You are a research assistant. Analyze the following context and "
        "identify research gaps.\n\n"
        "Context:\n{CONTEXT}\n\n"
        "Provide:\n"
        "1. Key research clusters\n"
        "2. Technical evolution\n"
        "3. Future opportunities\n"
    ),
    "hypothesis": (
        "You are a research assistant. Based on the following analysis, "
        "generate a testable hypothesis.\n\n"
        "Analysis:\n{ANALYSIS}\n\n"
        "Provide:\n"
        "1. Hypothesis statement\n"
        "2. Mathematical formulation (if applicable)\n"
        "3. Expected outcome\n"
    ),
    "method_design": (
        "You are a research assistant. Design a method to test the "
        "following hypothesis.\n\n"
        "Hypothesis:\n{HYPOTHESIS}\n\n"
        "Provide:\n"
        "1. Method overview\n"
        "2. Architecture\n"
        "3. Key components\n"
    ),
    "experiment_design": (
        "You are a research assistant. Design an experiment to validate "
        "the following method.\n\n"
        "Method:\n{METHOD}\n\n"
        "Provide:\n"
        "1. Datasets\n"
        "2. Models\n"
        "3. Metrics\n"
        "4. Evaluation protocol\n"
    ),
    "default": (
        "You are a research assistant. Respond to the following prompt.\n\n"
        "{PROMPT}\n"
    ),
}


class PromptManager:
    """
    Manages loading, caching, and rendering of prompt templates.

    Attributes:
        templates_dir: Directory containing template files.
        _cache: In-memory cache of loaded templates.
    """

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        """
        Initialize the PromptManager.

        Args:
            templates_dir: Path to the directory containing template files.
                           If None, uses the default
                           ``infrastructure/llm/templates/`` directory.
        """
        self.templates_dir = Path(templates_dir) if templates_dir else _DEFAULT_TEMPLATES_DIR
        self._cache: Dict[str, str] = {}
        logger.info("PromptManager initialised, templates_dir=%s", self.templates_dir)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_template(self, name: str) -> str:
        """
        Load a prompt template by name.

        First checks the in-memory cache, then tries to load from the
        templates directory (trying both ``<name>`` and ``<name>.txt``).
        If no file is found, returns a built-in fallback template.

        Args:
            name: Template name (with or without file extension).

        Returns:
            The template content string.
        """
        # Normalise: strip .txt/.md extension for cache key
        cache_key = name
        if cache_key.endswith(".txt"):
            cache_key = cache_key[:-4]
        elif cache_key.endswith(".md"):
            cache_key = cache_key[:-3]

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try loading from file
        content = self._load_from_file(name) or self._load_from_file(cache_key)

        if content is None:
            # Fallback to built-in template
            content = _FALLBACK_TEMPLATES.get(cache_key, _FALLBACK_TEMPLATES["default"])
            logger.warning(
                "Template '%s' not found in %s, using fallback",
                name, self.templates_dir,
            )

        self._cache[cache_key] = content
        logger.info("Loaded prompt template: %s (%d chars)", cache_key, len(content))
        return content

    def _load_from_file(self, name: str) -> Optional[str]:
        """Try to load a template file, trying common extensions."""
        candidates = [
            self.templates_dir / name,
            self.templates_dir / f"{name}.txt",
            self.templates_dir / f"{name}.md",
        ]
        for candidate in candidates:
            if candidate.is_file():
                try:
                    return candidate.read_text(encoding="utf-8")
                except OSError as e:
                    logger.warning("Failed to read template %s: %s", candidate, e)
        return None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, name: str, **kwargs: object) -> str:
        """
        Load a template and substitute variables.

        Uses a safe format_map that leaves unresolvable placeholders
        in place (rather than raising KeyError).

        Args:
            name:     Template name.
            **kwargs: Variables to substitute into the template.

        Returns:
            Rendered prompt string with variables replaced.
        """
        template = self.load_template(name)
        return self._safe_format(template, kwargs)

    def render_template(self, template_str: str, **kwargs: object) -> str:
        """
        Render a raw template string (not loaded from file).

        Args:
            template_str: Raw template content.
            **kwargs:     Variables to substitute.

        Returns:
            Rendered string.
        """
        return self._safe_format(template_str, kwargs)

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_templates(self) -> List[str]:
        """
        List all available template names.

        Scans the templates directory for ``.txt`` and ``.md`` files
        and also includes built-in fallback template names.

        Returns:
            Sorted list of template names (without extensions).
        """
        names: set[str] = set()

        # File-based templates
        if self.templates_dir.is_dir():
            for f in self.templates_dir.iterdir():
                if f.is_file() and f.suffix in (".txt", ".md"):
                    names.add(f.stem)

        # Built-in fallback templates
        names.update(_FALLBACK_TEMPLATES.keys())

        return sorted(names)

    def clear_cache(self) -> None:
        """Clear the in-memory template cache."""
        self._cache.clear()
        logger.info("Prompt template cache cleared")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_format(template: str, variables: Dict[str, object]) -> str:
        """
        Substitute {VARIABLE} placeholders in *template* using *variables*.

        Unmatched placeholders are left as-is (no error raised).
        """

        class _SafeDict(dict):
            """Dict subclass that returns the original key for missing items."""

            def __missing__(self, key: str) -> str:
                return "{" + key + "}"

        # Convert all values to strings for substitution
        str_vars = {k: str(v) for k, v in variables.items()}
        return template.format_map(_SafeDict(str_vars))
