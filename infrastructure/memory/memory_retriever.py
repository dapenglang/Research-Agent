"""
Memory retriever with weighted relevance scoring for Research Agent v3.

Relevance score weights (user-adjusted):
  keyword_similarity:     25%
  semantic_similarity:    25%
  domain_compatibility:   20%
  module_compatibility:   15%
  verification:           10%
  time_relevance:          5%

Domain compatibility:
  - If the memory item's domain matches the current research domain: full score.
  - If cross_domain is disabled and domains differ: 0 for domain_compatibility.
  - If cross_domain is enabled: partial score based on domain relatedness.

The retriever returns items sorted by relevance score and logs each
retrieval event via the UsageLogger.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from Research_Agent_v3.infrastructure.memory.memory_store import MemoryStore
from Research_Agent_v3.infrastructure.memory.usage_logger import UsageLogger

logger = logging.getLogger(__name__)

# ============================================================
# Relevance score weights (user-adjusted)
# ============================================================

WEIGHTS: Dict[str, float] = {
    "keyword_similarity": 0.25,
    "semantic_similarity": 0.25,
    "domain_compatibility": 0.20,
    "module_compatibility": 0.15,
    "verification": 0.10,
    "time_relevance": 0.05,
}

# Module keyword mappings: module_id -> typical keywords
_MODULE_KEYWORDS: Dict[str, Set[str]] = {
    "01_literature_retrieval": {"retrieval", "search", "database", "query", "paper", "literature"},
    "02_source_acquisition": {"download", "acquire", "source", "pdf", "arxiv", "url"},
    "03_literature_intelligence": {"analysis", "intelligence", "extraction", "understanding", "parse"},
    "04_research_landscape": {"landscape", "survey", "overview", "mapping", "trend"},
    "05_innovation_reasoning": {"innovation", "novelty", "gap", "hypothesis", "creative"},
    "06_theory_method": {"theory", "method", "design", "architecture", "formulation"},
    "07_experiment_planning": {"experiment", "plan", "design", "protocol", "setup"},
    "08_synthetic_experiment_engine": {"synthetic", "simulation", "engine", "mock", "generate"},
    "09_real_experiment_engine": {"real", "experiment", "run", "execute", "benchmark"},
    "10_result_analysis": {"result", "analysis", "evaluation", "metric", "performance"},
    "11_figure_table": {"figure", "table", "visualization", "chart", "plot"},
    "12_paper_writing": {"writing", "paper", "draft", "manuscript", "latex"},
    "13_reference_supplementary": {"reference", "supplementary", "citation", "appendix"},
}


class MemoryRetriever:
    """
    Retrieves relevant memory items using weighted relevance scoring.

    Usage:
        retriever = MemoryRetriever(memory_store, usage_logger)
        items = retriever.retrieve(
            research_task={
                "task_id": "task_001",
                "domain": "vlm_safety",
                "query": "cross-modal safety defense framework",
                "keywords": ["safety", "cross-modal", "defense"],
            },
            module_id="05_innovation_reasoning",
            max_items=20,
        )
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        usage_logger: Optional[UsageLogger] = None,
        cross_domain: bool = False,
    ) -> None:
        """
        Initialize the MemoryRetriever.

        Args:
            memory_store: The MemoryStore to search.
            usage_logger: Optional UsageLogger for logging retrievals.
                          If None, logging is skipped.
            cross_domain: If True, memory items from other domains
                          receive a partial domain_compatibility score
                          instead of 0.
        """
        self._store = memory_store
        self._logger = usage_logger
        self._cross_domain = cross_domain

        logger.info(
            "MemoryRetriever initialised (cross_domain=%s)",
            self._cross_domain,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        research_task: Dict[str, Any],
        module_id: str,
        max_items: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memory items for a research task and module.

        Searches all three memory layers (universal, domains, projects),
        scores each item, and returns the top-N items sorted by score.

        Args:
            research_task: Dict with keys:
                             - task_id (str): Current task ID
                             - domain (str): Current research domain
                             - query (str): Query text
                             - keywords (list[str]): Query keywords
            module_id:     The module requesting memory.
            max_items:     Maximum items to return.

        Returns:
            List of memory item dicts, each augmented with a
            ``relevance_score`` field, sorted by score (highest first).
        """
        task_id = research_task.get("task_id", "")
        domain = research_task.get("domain", "")
        query_text = research_task.get("query", "")
        keywords = research_task.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        # Gather items from all layers
        all_items: List[Dict[str, Any]] = []

        # Universal layer
        all_items.extend(self._store.retrieve_all("universal"))

        # Domain layer (current domain + others if cross_domain)
        if self._cross_domain:
            # Retrieve from all domains
            domain_items = self._store.retrieve("domains", {})
            all_items.extend(domain_items)
        else:
            # Only from current domain
            if domain:
                domain_items = self._store.retrieve("domains", {"domain": domain})
                all_items.extend(domain_items)

        # Project layer (current task only)
        if task_id:
            project_items = self._store.retrieve("projects", {"task_id": task_id})
            all_items.extend(project_items)

        # Also include universal items from other tasks if cross_domain
        # (universal layer is already included above)

        logger.info(
            "Retrieved %d candidate items from memory store", len(all_items)
        )

        # Score each item
        scored: List[tuple[float, Dict[str, Any]]] = []
        for item in all_items:
            score = self.score_relevance(item, research_task, module_id)
            if score > 0.0:
                item_copy = dict(item)
                item_copy["relevance_score"] = round(score, 4)
                scored.append((score, item_copy))

        # Sort by score (highest first) and limit
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item for _, item in scored[:max_items]]

        # Log each retrieval
        if self._logger:
            for item in results:
                self._log_retrieval(item, research_task, module_id)

        logger.info(
            "Returning %d relevant items (module=%s, domain=%s)",
            len(results), module_id, domain,
        )
        return results

    def score_relevance(
        self,
        item: Dict[str, Any],
        query: Dict[str, Any],
        module_id: str,
    ) -> float:
        """
        Compute the weighted relevance score for a memory item.

        Score components (weights):
          keyword_similarity:     25%  — overlap between query keywords and item content
          semantic_similarity:    25%  — word-level overlap between query text and content
          domain_compatibility:   20%  — domain match between item and query
          module_compatibility:   15%  — how well the item type matches module needs
          verification:           10%  — bonus for verified items
          time_relevance:          5%  — recency of the memory item

        Args:
            item:      Memory item dict.
            query:     Research task dict (with domain, query, keywords, task_id).
            module_id: The requesting module's ID.

        Returns:
            Relevance score in [0.0, 1.0].
        """
        scores: Dict[str, float] = {}

        # 1. Keyword similarity (25%)
        scores["keyword_similarity"] = self._score_keyword_similarity(item, query)

        # 2. Semantic similarity (25%)
        scores["semantic_similarity"] = self._score_semantic_similarity(item, query)

        # 3. Domain compatibility (20%)
        scores["domain_compatibility"] = self._score_domain_compatibility(item, query)

        # 4. Module compatibility (15%)
        scores["module_compatibility"] = self._score_module_compatibility(item, module_id)

        # 5. Verification (10%)
        scores["verification"] = self._score_verification(item)

        # 6. Time relevance (5%)
        scores["time_relevance"] = self._score_time_relevance(item)

        # Weighted sum
        total = sum(scores.get(name, 0.0) * weight for name, weight in WEIGHTS.items())

        return min(max(total, 0.0), 1.0)

    def get_weights(self) -> Dict[str, float]:
        """Return a copy of the current scoring weights."""
        return dict(WEIGHTS)

    def set_cross_domain(self, enabled: bool) -> None:
        """Enable or disable cross-domain retrieval."""
        self._cross_domain = enabled
        logger.info("Cross-domain retrieval set to %s", enabled)

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Split text into lowercase word tokens."""
        if not text:
            return set()
        return set(re.findall(r"\b[a-z0-9_]+\b", text.lower()))

    def _score_keyword_similarity(self, item: Dict[str, Any], query: Dict[str, Any]) -> float:
        """
        Score keyword overlap between query keywords and item content.

        Returns the fraction of query keywords found in the item's
        content (case-insensitive).
        """
        keywords = query.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        if not keywords:
            return 0.0

        content = (item.get("content", "") + " " + item.get("type", "")).lower()
        evidence_text = " ".join(str(e) for e in item.get("evidence", []))
        full_text = (content + " " + evidence_text).lower()

        matched = sum(1 for kw in keywords if kw.lower() in full_text)
        return matched / len(keywords)

    def _score_semantic_similarity(self, item: Dict[str, Any], query: Dict[str, Any]) -> float:
        """
        Score word-level overlap between query text and item content.

        Uses Jaccard similarity on word token sets.
        """
        query_text = query.get("query", "")
        item_text = item.get("content", "") + " " + item.get("type", "")

        query_tokens = self._tokenize(query_text)
        item_tokens = self._tokenize(item_text)

        if not query_tokens or not item_tokens:
            return 0.0

        intersection = query_tokens & item_tokens
        union = query_tokens | item_tokens

        return len(intersection) / len(union) if union else 0.0

    def _score_domain_compatibility(self, item: Dict[str, Any], query: Dict[str, Any]) -> float:
        """
        Score domain compatibility between item and query.

        - Same domain: 1.0
        - Universal layer (no domain): 0.5 (broadly applicable)
        - Cross-domain enabled, different domain: 0.3 (partial)
        - Cross-domain disabled, different domain: 0.0
        """
        item_domain = item.get("domain", "")
        query_domain = query.get("domain", "")

        # Universal items (no domain) are broadly applicable
        if not item_domain:
            return 0.5

        # Same domain
        if item_domain == query_domain:
            return 1.0

        # Different domain
        if self._cross_domain:
            # Check for domain relatedness (shared tokens)
            item_tokens = self._tokenize(item_domain)
            query_tokens = self._tokenize(query_domain)
            if item_tokens and query_tokens:
                overlap = item_tokens & query_tokens
                if overlap:
                    return 0.6
            return 0.3
        else:
            return 0.0

    def _score_module_compatibility(
        self, item: Dict[str, Any], module_id: str
    ) -> float:
        """
        Score how well a memory item matches a module's typical needs.

        Checks if the item's type or content keywords align with the
        module's expected keywords.
        """
        module_keywords = _MODULE_KEYWORDS.get(module_id, set())
        if not module_keywords:
            return 0.3  # Unknown module: neutral score

        item_text = (
            item.get("type", "") + " " + item.get("content", "")
        ).lower()
        item_tokens = self._tokenize(item_text)

        if not item_tokens:
            return 0.0

        overlap = module_tokens & item_tokens if (module_tokens := module_keywords) else set()
        if not overlap:
            return 0.1

        return min(len(overlap) / max(len(module_keywords) * 0.3, 1.0), 1.0)

    @staticmethod
    def _score_verification(item: Dict[str, Any]) -> float:
        """
        Score based on verification status.

        - Verified: 1.0
        - Not verified: 0.3
        """
        return 1.0 if item.get("verified", False) else 0.3

    @staticmethod
    def _score_time_relevance(item: Dict[str, Any]) -> float:
        """
        Score based on recency of the memory item.

        Uses exponential decay: newer items score higher.
        Half-life is approximately 90 days.
        """
        created_at = item.get("created_at", "")
        if not created_at:
            return 0.3

        try:
            # Parse ISO 8601 timestamp
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            # Handle naive datetime
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            age_days = (now - created).total_seconds() / 86400.0

            # Exponential decay with 90-day half-life
            import math
            score = math.exp(-age_days / 90.0)
            return max(score, 0.05)  # Floor at 0.05

        except (ValueError, TypeError):
            return 0.3

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_retrieval(
        self,
        item: Dict[str, Any],
        research_task: Dict[str, Any],
        module_id: str,
    ) -> None:
        """Log a memory retrieval event via the UsageLogger."""
        if not self._logger:
            return

        memory_id = item.get("memory_id", "unknown")
        task_id = research_task.get("task_id", "unknown")
        domain = research_task.get("domain", "unknown")
        score = item.get("relevance_score", 0.0)

        # Determine retrieval reason
        keywords = research_task.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        reason = (
            f"keyword match: {', '.join(keywords[:3])}"
            if keywords
            else f"semantic match on '{research_task.get('query', '')[:50]}'"
        )

        self._logger.log(
            memory_id=memory_id,
            source_task=task_id,
            source_domain=domain,
            relevance_score=score,
            retrieval_reason=reason,
            injected_to_module=module_id,
            impact_on_decision="pending",  # Updated by the module after use
        )
