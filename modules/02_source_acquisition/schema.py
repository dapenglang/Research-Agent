"""
Module 02 — Source Acquisition & Parsing
Input/output schema definitions.

Defines the structure of input and output files for Module 02,
including field types, required/optional flags, and validation rules.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Input file schemas
# ---------------------------------------------------------------------------

INPUT_FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "download_queue.json": {
        "fields": {
        "queue": {"type": "List[Dict]", "required": True},
        "queue[].paper_id": {"type": "str", "required": True},
        "queue[].url": {"type": "str", "required": True},
        "queue[].source_db": {"type": "str", "required": True},
        }
    },
}


# ---------------------------------------------------------------------------
# Output file schemas
# ---------------------------------------------------------------------------

OUTPUT_FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "papers/<paper_id>/metadata.json": {
        "fields": {
        "paper_id": {"type": "str", "required": True},
        "title": {"type": "str", "required": True},
        "authors": {"type": "List[str]", "required": True},
        "year": {"type": "int", "required": True},
        "doi": {"type": "str", "required": False},
        "pages": {"type": "int", "required": False},
        }
    },
    "papers/<paper_id>/normalized/paper.md": {
        "fields": {
        "content": {"type": "str", "required": True},
        "sections": {"type": "List[Dict]", "required": True},
        "section[].heading": {"type": "str", "required": True},
        "section[].content": {"type": "str", "required": True},
        }
    },
    "papers/<paper_id>/equations.json": {
        "fields": {
        "equations": {"type": "List[Dict]", "required": True},
        "equations[].latex": {"type": "str", "required": True},
        "equations[].label": {"type": "str", "required": False},
        "equations[].page": {"type": "int", "required": False},
        }
    },
    "papers/<paper_id>/figures.json": {
        "fields": {
        "figures": {"type": "List[Dict]", "required": True},
        "figures[].caption": {"type": "str", "required": True},
        "figures[].page": {"type": "int", "required": False},
        }
    },
    "papers/<paper_id>/tables.json": {
        "fields": {
        "tables": {"type": "List[Dict]", "required": True},
        "tables[].caption": {"type": "str", "required": True},
        "tables[].rows": {"type": "List[List[str]]", "required": False},
        }
    },
    "papers/<paper_id>/citations.json": {
        "fields": {
        "citations": {"type": "List[Dict]", "required": True},
        "citations[].raw_text": {"type": "str", "required": True},
        "citations[].key": {"type": "str", "required": False},
        }
    },
    "papers/<paper_id>/provenance.json": {
        "fields": {
        "paper_id": {"type": "str", "required": True},
        "download_url": {"type": "str", "required": True},
        "download_timestamp": {"type": "str", "required": True},
        "parser_version": {"type": "str", "required": True},
        "source_hash": {"type": "str", "required": True},
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
