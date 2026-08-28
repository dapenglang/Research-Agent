"""
Module 08 — Synthetic Experiment Engine
Input/output schema definitions.

Defines the structure of input and output files for Module 08,
including field types, required/optional flags, and validation rules.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Input file schemas
# ---------------------------------------------------------------------------

INPUT_FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "method_spec.json": {
        "fields": {
        "method_name": {"type": "str", "required": True},
        "components": {"type": "List[Dict]", "required": True},
        "hyperparameters": {"type": "Dict[str, Any]", "required": False},
        }
    },
    "experiment_matrix.yaml": {
        "fields": {
        "experiments": {"type": "List[Dict]", "required": True},
        "experiments[].id": {"type": "str", "required": True},
        "experiments[].data_origin": {"type": "str", "required": True, "must_be": 'synthetic'},
        "experiments[].parameters": {"type": "Dict[str, Any]", "required": True},
        }
    },
    "claim_evidence_plan.json": {
        "fields": {
        "claims": {"type": "List[Dict]", "required": True},
        "claims[].id": {"type": "str", "required": True},
        "claims[].pass_criteria": {"type": "Dict[str, Any]", "required": True},
        }
    },
}


# ---------------------------------------------------------------------------
# Output file schemas
# ---------------------------------------------------------------------------

OUTPUT_FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "synthetic_results/metrics.csv": {
        "fields": {
        "experiment_id": {"type": "str", "required": True},
        "metric_name": {"type": "str", "required": True},
        "metric_value": {"type": "float", "required": True},
        "data_origin": {"type": "str", "required": True, "must_be": 'synthetic'},
        }
    },
    "synthetic_results/statistics.json": {
        "fields": {
        "experiment_id": {"type": "str", "required": True},
        "summary_stats": {"type": "Dict[str, float]", "required": True},
        "confidence_intervals": {"type": "Dict[str, List[float]]", "required": False},
        "data_origin": {"type": "str", "required": True, "must_be": 'synthetic'},
        }
    },
    "synthetic_results/provenance.json": {
        "fields": {
        "experiments_run": {"type": "List[str]", "required": True},
        "execution_timestamp": {"type": "str", "required": True},
        "adapter_used": {"type": "str", "required": True},
        "adapter_version": {"type": "str", "required": True},
        "data_origin": {"type": "str", "required": True, "must_be": 'synthetic'},
        "environment": {"type": "Dict[str, str]", "required": True},
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
