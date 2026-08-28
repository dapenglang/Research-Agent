"""Reasoning graph stub."""
from typing import Dict, List, Any

class ReasoningGraph:
    def __init__(self, **kwargs):
        self.nodes = []
        self.edges = []

    def add_node(self, node_id: str, node_type: str, content: str) -> None:
        self.nodes.append({"id": node_id, "type": node_type, "content": content})

    def add_edge(self, source: str, target: str, relation: str = "leads_to") -> None:
        self.edges.append({"source": source, "target": target, "relation": relation})

    def build_chain(self, items: List[Dict]) -> None:
        for i, item in enumerate(items):
            self.add_node(f"node_{i}", item.get("type", "unknown"), item.get("content", ""))
            if i > 0:
                self.add_edge(f"node_{i-1}", f"node_{i}")

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}
