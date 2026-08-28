"""Contradiction detector stub."""
from typing import Dict, List, Any, Optional

class ContradictionDetector:
    def __init__(self, llm_provider=None, llm_enabled: bool = False, **kwargs):
        self.llm_provider = llm_provider
        self.llm_enabled = llm_enabled

    def detect(self, papers: List[Dict]) -> Dict[str, Any]:
        return {"contradictions": [], "count": 0}
