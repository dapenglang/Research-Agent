"""
Tests for research_task.yaml configuration support.

Validates that the formal research task template at
configs/research_task_template.yaml supports all required fields
and that the research_context_extractor correctly reads them.

Test coverage:
  - domain can be read
  - topic can be read
  - keywords can be read
  - research_question can be read
  - literature targets can be read
  - synthetic/real policy can be read
  - unknown/missing required fields produce clear errors
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from infrastructure.research_context_extractor import (
    extract_research_context,
    validate_research_task,
)

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

TEMPLATE_PATH = _PROJECT_ROOT / "configs" / "research_task_template.yaml"
E2E_PATH = _PROJECT_ROOT / "tests" / "e2e_test_data" / "research_task.yaml"


@pytest.fixture
def template_config() -> dict:
    """Load the formal template YAML."""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def e2e_config() -> dict:
    """Load the E2E test YAML."""
    with open(E2E_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


VALID_FULL_CONFIG = {
    "task_id": "test_001",
    "title": "Test Research",
    "research": {
        "domain": "computer_vision",
        "topic": "Adversarial Robustness",
        "keywords": ["adversarial", "VLM", "robustness"],
        "research_question": "How do adversarial patches affect VLMs?",
        "target": "LLaVA-1.5-7B",
    },
    "literature": {
        "candidate_target": ["paper_001"],
        "core_target": ["paper_002"],
        "deep_analysis_target": ["paper_003"],
        "arxiv": {
            "download_pdf": True,
            "download_source": False,
            "prefer_latex_analysis": True,
        },
    },
    "experiment": {
        "method": "samra",
        "synthetic": {"num_samples": 50, "seed": 42},
        "real": {"checkpoint_dir": "ckpt", "seed": 7},
    },
    "llm": {"type": "openai"},
}


# --------------------------------------------------------------------------- #
# Template existence
# --------------------------------------------------------------------------- #

class TestTemplateExists:
    def test_template_file_exists(self):
        assert TEMPLATE_PATH.exists(), (
            f"Formal template not found at {TEMPLATE_PATH}"
        )

    def test_e2e_file_still_exists(self):
        assert E2E_PATH.exists(), (
            f"E2E test config should still exist at {E2E_PATH}"
        )


# --------------------------------------------------------------------------- #
# Field readability from formal template
# --------------------------------------------------------------------------- #

class TestTemplateFieldReading:
    def test_domain_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["domain"] == "computer_vision"

    def test_topic_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["topic"] != ""

    def test_keywords_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert isinstance(ctx["keywords"], list)
        assert len(ctx["keywords"]) >= 1

    def test_research_question_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["research_question"] != ""

    def test_target_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["target"] != ""

    def test_literature_targets_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert "candidate_target" in ctx
        assert "core_target" in ctx
        assert "deep_analysis_target" in ctx
        assert isinstance(ctx["candidate_target"], list)
        assert isinstance(ctx["core_target"], list)
        assert isinstance(ctx["deep_analysis_target"], list)

    def test_arxiv_settings_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["arxiv_download_pdf"] is True
        assert ctx["arxiv_download_source"] is False
        assert ctx["arxiv_prefer_latex"] is True

    def test_synthetic_policy_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["synthetic_enabled"] is True
        assert isinstance(ctx["synthetic_config"], dict)
        assert "num_samples" in ctx["synthetic_config"]

    def test_real_policy_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["real_enabled"] is True
        assert isinstance(ctx["real_config"], dict)
        assert "seed" in ctx["real_config"]

    def test_llm_type_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["llm_type"] == "openai"

    def test_experiment_method_readable(self, template_config):
        ctx = extract_research_context(template_config)
        assert ctx["experiment_method"] == "samra"


# --------------------------------------------------------------------------- #
# Full config extraction
# --------------------------------------------------------------------------- #

class TestFullConfigExtraction:
    def test_all_fields_extracted(self):
        ctx = extract_research_context(VALID_FULL_CONFIG)
        assert ctx["domain"] == "computer_vision"
        assert ctx["topic"] == "Adversarial Robustness"
        assert ctx["keywords"] == ["adversarial", "VLM", "robustness"]
        assert ctx["research_question"] == "How do adversarial patches affect VLMs?"
        assert ctx["target"] == "LLaVA-1.5-7B"
        assert ctx["candidate_target"] == ["paper_001"]
        assert ctx["core_target"] == ["paper_002"]
        assert ctx["deep_analysis_target"] == ["paper_003"]
        assert ctx["arxiv_download_pdf"] is True
        assert ctx["arxiv_download_source"] is False
        assert ctx["arxiv_prefer_latex"] is True
        assert ctx["synthetic_enabled"] is True
        assert ctx["real_enabled"] is True
        assert ctx["llm_type"] == "openai"
        assert ctx["experiment_method"] == "samra"


# --------------------------------------------------------------------------- #
# Backward compatibility — flat format (E2E test config)
# --------------------------------------------------------------------------- #

class TestBackwardCompatibility:
    def test_e2e_config_does_not_crash(self, e2e_config):
        ctx = extract_research_context(e2e_config)
        # E2E config has no research section — fields should be empty/default
        assert ctx["domain"] == ""
        assert ctx["keywords"] == []
        assert ctx["research_question"] == ""
        # But experiment fields should still work
        assert ctx["experiment_method"] == "samra"
        assert ctx["synthetic_enabled"] is True

    def test_flat_format_supported(self):
        flat_config = {
            "task_id": "flat_001",
            "keywords": ["flat_keyword"],
            "research_question": "Flat question?",
            "domain": "nlp",
        }
        ctx = extract_research_context(flat_config)
        assert ctx["domain"] == "nlp"
        assert ctx["keywords"] == ["flat_keyword"]
        assert ctx["research_question"] == "Flat question?"

    def test_nested_takes_precedence_over_flat(self):
        config = {
            "research": {
                "domain": "nested_domain",
                "keywords": ["nested_kw"],
                "research_question": "Nested question?",
            },
            "domain": "flat_domain",
            "keywords": ["flat_kw"],
            "research_question": "Flat question?",
        }
        ctx = extract_research_context(config)
        assert ctx["domain"] == "nested_domain"
        assert ctx["keywords"] == ["nested_kw"]
        assert ctx["research_question"] == "Nested question?"


# --------------------------------------------------------------------------- #
# Validation — missing required fields
# --------------------------------------------------------------------------- #

class TestValidationMissingFields:
    def test_valid_config_no_errors(self):
        errors = validate_research_task(VALID_FULL_CONFIG)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_template_config_no_errors(self, template_config):
        errors = validate_research_task(template_config)
        assert errors == [], f"Template should be valid, got: {errors}"

    def test_missing_domain(self):
        config = {
            "task_id": "test_002",
            "title": "Test",
            "research": {
                "keywords": ["kw"],
                "research_question": "Question?",
            },
            "llm": {"type": "openai"},
        }
        errors = validate_research_task(config)
        assert any("domain" in e for e in errors), (
            f"Should report missing domain, got: {errors}"
        )

    def test_missing_keywords(self):
        config = {
            "task_id": "test_003",
            "title": "Test",
            "research": {
                "domain": "cv",
                "research_question": "Question?",
            },
            "llm": {"type": "openai"},
        }
        errors = validate_research_task(config)
        assert any("keywords" in e for e in errors), (
            f"Should report missing keywords, got: {errors}"
        )

    def test_missing_research_question(self):
        config = {
            "task_id": "test_004",
            "title": "Test",
            "research": {
                "domain": "cv",
                "keywords": ["kw"],
            },
            "llm": {"type": "openai"},
        }
        errors = validate_research_task(config)
        assert any("research_question" in e for e in errors), (
            f"Should report missing research_question, got: {errors}"
        )

    def test_missing_task_id(self):
        config = {
            "title": "No Task ID",
            "research": {
                "domain": "cv",
                "keywords": ["kw"],
                "research_question": "Q?",
            },
            "llm": {"type": "openai"},
        }
        errors = validate_research_task(config)
        assert any("task_id" in e for e in errors), (
            f"Should report missing task_id, got: {errors}"
        )

    def test_missing_title(self):
        config = {
            "task_id": "test_005",
            "research": {
                "domain": "cv",
                "keywords": ["kw"],
                "research_question": "Q?",
            },
            "llm": {"type": "openai"},
        }
        errors = validate_research_task(config)
        assert any("title" in e for e in errors), (
            f"Should report missing title, got: {errors}"
        )

    def test_missing_llm_type(self):
        config = {
            "task_id": "test_006",
            "title": "Test",
            "research": {
                "domain": "cv",
                "keywords": ["kw"],
                "research_question": "Q?",
            },
        }
        errors = validate_research_task(config)
        assert any("llm" in e.lower() for e in errors), (
            f"Should report missing llm.type, got: {errors}"
        )

    def test_empty_config_produces_errors(self):
        errors = validate_research_task({})
        assert len(errors) >= 3, (
            f"Empty config should produce multiple errors, got: {errors}"
        )

    def test_all_missing_required_fields_reported(self):
        config = {"task_id": "", "title": ""}
        errors = validate_research_task(config)
        error_text = " ".join(errors)
        assert "domain" in error_text
        assert "keywords" in error_text
        assert "research_question" in error_text
        assert "task_id" in error_text
        assert "title" in error_text


# --------------------------------------------------------------------------- #
# Unknown fields — should not crash
# --------------------------------------------------------------------------- #

class TestUnknownFields:
    def test_unknown_fields_ignored(self):
        config = {
            "task_id": "test_007",
            "title": "Test",
            "research": {
                "domain": "cv",
                "keywords": ["kw"],
                "research_question": "Q?",
            },
            "llm": {"type": "openai"},
            "unknown_section": {"foo": "bar"},
            "random_field": 42,
        }
        ctx = extract_research_context(config)
        assert ctx["domain"] == "cv"
        errors = validate_research_task(config)
        assert errors == [], f"Unknown fields should not cause errors: {errors}"
