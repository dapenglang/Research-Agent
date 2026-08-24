"""Module 02.5 schema definitions."""

MODULE_SCHEMA = {
    "module_id": "02_5",
    "module_name": "Paper Asset Intelligence",
    "description": "Extracts and saves first 3 figures from papers",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "upstream_module_02": {"type": "object"},
        },
        "required": ["task_id"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "paper_assets.json": {"type": "string"},
        },
    },
}
