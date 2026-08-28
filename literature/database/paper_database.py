"""Paper database — stores and retrieves paper metadata."""
import json
import os
from typing import List, Dict, Any, Optional


class PaperDatabase:
    def __init__(self, db_path: str = "papers_db.json", **kwargs):
        self.db_path = db_path
        self._papers: Dict[str, Dict] = {}
        if os.path.exists(db_path):
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    self._papers = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._papers = {}

    def add(self, knowledge: Dict[str, Any]) -> None:
        """Add a knowledge dict to the database.

        Accepts either a single dict (with paper_id field) or
        (paper_id, metadata) as two arguments for backwards compatibility.
        """
        if isinstance(knowledge, dict):
            paper_id = knowledge.get("paper_id", knowledge.get("title", str(len(self._papers))))
            self._papers[paper_id] = knowledge
        self._save()

    def get(self, paper_id: str) -> Optional[Dict]:
        return self._papers.get(paper_id)

    def search(self, query: str) -> List[Dict]:
        results = []
        query_lower = query.lower()
        for pid, meta in self._papers.items():
            if query_lower in json.dumps(meta, ensure_ascii=False).lower():
                results.append({"paper_id": pid, **meta})
        return results

    def all(self) -> Dict[str, Dict]:
        return self._papers

    def save(self, path: str = None) -> None:
        """Public save method — persists the database to disk.

        Args:
            path: Optional path to save to. If None, uses the default db_path.
        """
        if path:
            self._save_to(path)
        else:
            self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._papers, f, indent=2, ensure_ascii=False)

    def _save_to(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._papers, f, indent=2, ensure_ascii=False)
