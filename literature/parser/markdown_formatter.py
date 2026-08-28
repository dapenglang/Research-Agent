"""Markdown formatter stub."""
from typing import Dict

class MarkdownFormatter:
    def __init__(self, **kwargs):
        pass

    def format(self, sections: Dict[str, str], title: str = "") -> str:
        lines = []
        if title:
            lines.append(f"# {title}\n")
        for name, content in sections.items():
            lines.append(f"## {name.title()}\n\n{content}\n")
        return "\n".join(lines)
