"""
Module 01 — Literature Retrieval
Input/output schema definitions.

Defines the structure of input and output files for Module 01,
including field types, required/optional flags, and validation rules.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Input file schemas
# ---------------------------------------------------------------------------

INPUT_FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "research_task.yaml": {
        "fields": {
        # Task identity (top-level, required)
        "task_id": {"type": "str", "required": True},
        "title": {"type": "str", "required": True},

        # Research content (nested under 'research', required for formal tasks)
        "research.domain": {"type": "str", "required": True},
        "research.topic": {"type": "str", "required": False},
        "research.keywords": {"type": "List[str]", "required": True},
        "research.research_question": {"type": "str", "required": True},
        "research.target": {"type": "str", "required": False},

        # Literature acquisition (nested under 'literature', optional)
        "literature.candidate_target": {"type": "List[str]", "required": False, "default": []},
        "literature.core_target": {"type": "List[str]", "required": False, "default": []},
        "literature.deep_analysis_target": {"type": "List[str]", "required": False, "default": []},
        "literature.arxiv.download_pdf": {"type": "bool", "required": False, "default": True},
        "literature.arxiv.download_source": {"type": "bool", "required": False, "default": False},
        "literature.arxiv.prefer_latex_analysis": {"type": "bool", "required": False, "default": True},

        # Experiment settings (nested under 'experiment', optional)
        "experiment.synthetic": {"type": "Dict", "required": False, "default": {}},
        "experiment.real": {"type": "Dict", "required": False, "default": {}},

        # Legacy flat fields (backward compatibility for E2E tests)
        "keywords": {"type": "List[str]", "required": False},
        "research_question": {"type": "str", "required": False},
        "domain": {"type": "str", "required": False},
        "max_papers": {"type": "int", "required": False, "default": 50},
        "databases": {"type": "List[str]", "required": False, "default": ["arxiv", "semantic_scholar", "openreview"]},
        }
    },
}


# ---------------------------------------------------------------------------
# Output file schemas
# ---------------------------------------------------------------------------

OUTPUT_FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "literature_manifest.json": {
        "fields": {
        "total_papers": {"type": "int", "required": True},
        "search_queries": {"type": "List[str]", "required": True},
        "databases_queried": {"type": "List[str]", "required": True},
        "retrieval_timestamp": {"type": "str", "required": True},
        }
    },
    "paper_metadata.jsonl": {
        "format": "jsonl", "fields": {
        "paper_id": {"type": "str", "required": True},
        "title": {"type": "str", "required": True},
        "authors": {"type": "List[str]", "required": True},
        "abstract": {"type": "str", "required": True},
        "year": {"type": "int", "required": True},
        "doi": {"type": "str", "required": False},
        "source_db": {"type": "str", "required": True},
        "url": {"type": "str", "required": False},
        "citation_count": {"type": "int", "required": False},
        }
    },
    "download_queue.json": {
        "fields": {
        "queue": {"type": "List[Dict]", "required": True},
        "queue[].paper_id": {"type": "str", "required": True},
        "queue[].url": {"type": "str", "required": True},
        "queue[].source_db": {"type": "str", "required": True},
        "queue[].priority": {"type": "int", "required": False, "default": 0},
        }
    },
}


# ---------------------------------------------------------------------------
# Schema helper dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FieldSpec:
    """Specification for a single field in a file schema."""
    field_name: str
    field_type: str
    required: bool = True
    default: Any = None
    must_be: Optional[Any] = None
    allowed: Optional[List[Any]] = None
    description: str = ""

    def validate_value(self, value: Any) -> bool:
        """Check if a value matches this field specification.

        Args:
            value: The value to validate.

        Returns:
            True if value is valid according to this spec.
        """
        if value is None:
            return not self.required
        if self.must_be is not None and value != self.must_be:
            return False
        if self.allowed is not None and value not in self.allowed:
            return False
        return True


@dataclass
class FileSchema:
    """Schema for a single input or output file."""
    filename: str
    fields: Dict[str, FieldSpec] = field(default_factory=dict)
    format: str = "json"  # json, jsonl, yaml, csv, md, tex, dir

    def validate_structure(self, data: Dict[str, Any]) -> List[str]:
        """Validate a data dictionary against this file schema.

        Args:
            data: The parsed data to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: List[str] = []
        for field_name, spec in self.fields.items():
            value = data.get(field_name)
            if value is None and spec.required:
                errors.append(f"Missing required field: {field_name}")
            elif value is not None and not spec.validate_value(value):
                errors.append(
                    f"Invalid value for field '{field_name}': "
                    f"expected type {spec.field_type}, got {type(value).__name__}"
                )
        return errors


def get_input_schema(filename: str) -> Optional[FileSchema]:
    """Retrieve the input file schema for a given filename.

    Args:
        filename: The input filename to look up.

        Returns:
            FileSchema if found, None otherwise.
    """
    raw = INPUT_FILE_SCHEMAS.get(filename)
    if raw is None:
        return None
    fields = {
        name: FieldSpec(
            field_name=name,
            field_type=spec.get("type", "str"),
            required=spec.get("required", False),
            default=spec.get("default"),
            must_be=spec.get("must_be"),
            allowed=spec.get("allowed"),
        )
        for name, spec in raw.get("fields", {}).items()
    }
    return FileSchema(
        filename=filename,
        fields=fields,
        format=raw.get("format", "json"),
    )


def get_output_schema(filename: str) -> Optional[FileSchema]:
    """Retrieve the output file schema for a given filename.

    Args:
        filename: The output filename to look up.

    Returns:
            FileSchema if found, None otherwise.
    """
    raw = OUTPUT_FILE_SCHEMAS.get(filename)
    if raw is None:
        return None
    fields = {
        name: FieldSpec(
            field_name=name,
            field_type=spec.get("type", "str"),
            required=spec.get("required", False),
            default=spec.get("default"),
            must_be=spec.get("must_be"),
            allowed=spec.get("allowed"),
        )
        for name, spec in raw.get("fields", {}).items()
    }
    return FileSchema(
        filename=filename,
        fields=fields,
        format=raw.get("format", "json"),
    )


def get_all_input_schemas() -> Dict[str, FileSchema]:
    """Retrieve all input file schemas for this module.

    Returns:
        Dictionary mapping filenames to FileSchema objects.
    """
    return {
        fname: get_input_schema(fname)
        for fname in INPUT_FILE_SCHEMAS
        if get_input_schema(fname) is not None
    }


def get_all_output_schemas() -> Dict[str, FileSchema]:
    """Retrieve all output file schemas for this module.

    Returns:
        Dictionary mapping filenames to FileSchema objects.
    """
    return {
        fname: get_output_schema(fname)
        for fname in OUTPUT_FILE_SCHEMAS
        if get_output_schema(fname) is not None
    }
