"""Section detector stub."""
from typing import Dict, List

class SectionDetector:
    def __init__(self, **kwargs):
        pass

    def detect(self, text: str) -> Dict[str, str]:
        sections = {}
        lower = text.lower()
        for name in ["abstract", "introduction", "related work", "method", "experiment", "results", "conclusion", "references"]:
            if name in lower:
                idx = lower.index(name)
                sections[name] = text[idx:idx+1000]
        return sections
