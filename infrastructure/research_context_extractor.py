"""
Research Context Extractor for Research Agent v3.

Extracts research fields from a parsed research_task.yaml configuration
dictionary, supporting both the formal nested format and the legacy
flat format for backward compatibility.

Nested format (formal template):
    research:
      domain, topic, keywords, research_question, target
    literature:
      candidate_target, core_target, deep_analysis_target, arxiv: {...}
    experiment:
      synthetic: {...}
      real: {...}

Flat format (legacy / E2E test):
    keywords, research_question, domain (at top level)

This module provides:
  - extract_research_context(task_config) -> dict
  - validate_research_task(task_config) -> list[str] (error messages)
"""

from __future__ import annotations

from typing import Any, Dict, List


def extract_research_context(task_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract research context from a parsed research_task.yaml dict.

    Supports both nested (research.keywords) and flat (keywords) formats.
    Nested takes precedence; flat is a fallback for legacy/E2E configs.

    Args:
        task_config: Parsed YAML dictionary from research_task.yaml.

    Returns:
        Flattened dictionary with all research context fields:
        - domain, topic, keywords, research_question, target
        - candidate_target, core_target, deep_analysis_target
        - arxiv_download_pdf, arxiv_download_source, arxiv_prefer_latex
        - synthetic_enabled, synthetic_config
        - real_enabled, real_config
        - max_papers, databases, llm_type
    """
    research = task_config.get("research", {}) or {}
    literature = task_config.get("literature", {}) or {}
    experiment = task_config.get("experiment", {}) or {}
    llm = task_config.get("llm", {}) or {}
    arxiv_cfg = literature.get("arxiv", {}) or {}

    keywords = research.get("keywords") or task_config.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]

    research_question = (
        research.get("research_question")
        or task_config.get("research_question", "")
    )

    domain = research.get("domain") or task_config.get("domain", "")
    topic = research.get("topic", "")
    target = research.get("target", "")

    return {
        "domain": domain,
        "topic": topic,
        "keywords": keywords,
        "research_question": research_question,
        "target": target,
        "candidate_target": literature.get("candidate_target", []),
        "core_target": literature.get("core_target", []),
        "deep_analysis_target": literature.get("deep_analysis_target", []),
        "arxiv_download_pdf": arxiv_cfg.get("download_pdf", True),
        "arxiv_download_source": arxiv_cfg.get("download_source", False),
        "arxiv_prefer_latex": arxiv_cfg.get("prefer_latex_analysis", True),
        "max_papers": task_config.get("max_papers", 50),
        "databases": task_config.get(
            "databases", ["arxiv", "semantic_scholar", "openreview"]
        ),
        "synthetic_enabled": bool(experiment.get("synthetic", {})),
        "synthetic_config": experiment.get("synthetic", {}),
        "real_enabled": bool(experiment.get("real", {})),
        "real_config": experiment.get("real", {}),
        "llm_type": llm.get("type", "mock"),
        "experiment_method": experiment.get("method", ""),
    }


# Required fields for a formal research task
REQUIRED_FIELDS = ["domain", "keywords", "research_question"]
REQUIRED_FIELD_PATHS = {
    "domain": ("research", "domain"),
    "keywords": ("research", "keywords"),
    "research_question": ("research", "research_question"),
}


def validate_research_task(task_config: Dict[str, Any]) -> List[str]:
    """Validate that a research_task.yaml has the required research fields.

    Checks both nested (research.X) and flat (X) formats. Reports clear
    error messages for each missing required field.

    Args:
        task_config: Parsed YAML dictionary from research_task.yaml.

    Returns:
        List of error strings (empty if valid).
    """
    errors: List[str] = []
    ctx = extract_research_context(task_config)

    if not task_config.get("task_id"):
        errors.append("Missing required field: 'task_id' (top-level)")

    if not task_config.get("title"):
        errors.append("Missing required field: 'title' (top-level)")

    for field_name in REQUIRED_FIELDS:
        value = ctx.get(field_name)
        if not value:
            nested_path = ".".join(REQUIRED_FIELD_PATHS[field_name])
            flat = field_name
            errors.append(
                f"Missing required field: '{field_name}' "
                f"(expected at '{nested_path}' or top-level '{flat}')"
            )

    llm = task_config.get("llm", {})
    if not llm or not llm.get("type"):
        errors.append("Missing required field: 'llm.type'")

    return errors
