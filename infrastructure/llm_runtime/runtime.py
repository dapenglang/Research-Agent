"""
LLM Runtime — unified LLM management with task-based routing, usage
tracking, and automatic fallback.

Loads providers.yaml and llm_routing.yaml to provide task-specific
LLM provider instances. Falls back to alternative providers when the
primary is unavailable or fails.

v8.3 additions:
  - Usage tracking: records call count, success/failure, estimated
    tokens per task type and provider.
  - Fallback chain: when a provider fails or is unavailable, tries
    the next configured fallback provider before giving up.
  - Usage report: generates llm_usage_report.json at pipeline end.

Usage:
    runtime = LLMRuntime()
    runtime.load()

    provider = runtime.get_provider("paper_generation")
    if provider:
        text = provider.generate("Write an abstract about...")

    # At pipeline end:
    runtime.save_usage_report("output/llm_usage_report.json")
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from Research_Agent_v3.infrastructure.llm.llm_provider import (
    LLMProvider,
    LLMProviderFactory,
    validate_usage,
)

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"

# Default fallback order: try these providers in sequence when primary fails
_DEFAULT_FALLBACK_ORDER = ["ollama_r1", "ollama", "deepseek", "openai", "mock"]


class UsageTracker:
    """Tracks LLM usage statistics per task type and provider."""

    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []

    def record(
        self,
        task_type: str,
        provider_name: str,
        model: str,
        success: bool,
        response_length: int = 0,
        prompt_length: int = 0,
        error: str = "",
        fallback_used: str = "",
    ) -> None:
        est_input_tokens = max(1, prompt_length // 4)
        est_output_tokens = max(1, response_length // 4)
        self._records.append({
            "task_type": task_type,
            "provider": provider_name,
            "model": model,
            "success": success,
            "prompt_length": prompt_length,
            "response_length": response_length,
            "est_input_tokens": est_input_tokens,
            "est_output_tokens": est_output_tokens,
            "est_total_tokens": est_input_tokens + est_output_tokens,
            "error": error,
            "fallback_used": fallback_used,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def get_summary(self) -> Dict[str, Any]:
        if not self._records:
            return {"total_calls": 0}
        total = len(self._records)
        successes = sum(1 for r in self._records if r["success"])
        failures = total - successes
        total_tokens = sum(r["est_total_tokens"] for r in self._records)
        per_task: Dict[str, Any] = {}
        for r in self._records:
            tt = r["task_type"]
            if tt not in per_task:
                per_task[tt] = {"calls": 0, "successes": 0, "tokens": 0}
            per_task[tt]["calls"] += 1
            per_task[tt]["successes"] += r["success"]
            per_task[tt]["tokens"] += r["est_total_tokens"]
        return {
            "total_calls": total,
            "total_successes": successes,
            "total_failures": failures,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "est_total_tokens": total_tokens,
            "per_task": per_task,
        }

    def to_list(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False, indent=2)


class _TrackedProvider(LLMProvider):
    """Wraps a provider and records usage on each generate() call."""

    def __init__(
        self,
        inner: LLMProvider,
        task_type: str,
        provider_name: str,
        tracker: UsageTracker,
    ) -> None:
        super().__init__(inner.model_name, inner.temperature, inner.max_tokens)
        self._inner = inner
        self._task_type = task_type
        self._provider_name = provider_name
        self._tracker = tracker

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            result = self._inner.generate(prompt, **kwargs)
            self._tracker.record(
                task_type=self._task_type,
                provider_name=self._provider_name,
                model=self._inner.model_name,
                success=True,
                response_length=len(result),
                prompt_length=len(prompt),
            )
            return result
        except Exception as e:
            self._tracker.record(
                task_type=self._task_type,
                provider_name=self._provider_name,
                model=self._inner.model_name,
                success=False,
                error=str(e),
                prompt_length=len(prompt),
            )
            raise

    def is_available(self) -> bool:
        return self._inner.is_available()

    def get_name(self) -> str:
        return f"Tracked({self._inner.get_name()})"


class LLMRuntime:
    """Manages LLM provider creation with task-based routing and fallback."""

    def __init__(self, configs_dir: Optional[str] = None) -> None:
        self._configs_dir = Path(configs_dir) if configs_dir else _CONFIGS_DIR
        self._providers_config: Dict[str, Any] = {}
        self._routing_config: Dict[str, Any] = {}
        self._provider_cache: Dict[str, LLMProvider] = {}
        self._loaded = False
        self._usage_tracker = UsageTracker()

    def load(self) -> None:
        """Load providers.yaml and llm_routing.yaml."""
        providers_path = self._configs_dir / "providers.yaml"
        routing_path = self._configs_dir / "llm_routing.yaml"

        if providers_path.exists():
            with open(providers_path, "r", encoding="utf-8") as f:
                self._providers_config = yaml.safe_load(f) or {}
            logger.info("Loaded providers config from %s", providers_path)
        else:
            logger.warning("providers.yaml not found at %s", providers_path)

        if routing_path.exists():
            with open(routing_path, "r", encoding="utf-8") as f:
                self._routing_config = yaml.safe_load(f) or {}
            logger.info("Loaded routing config from %s", routing_path)
        else:
            logger.warning("llm_routing.yaml not found at %s", routing_path)

        self._loaded = True

    def get_provider(self, task_type: str) -> Optional[LLMProvider]:
        """
        Get an LLM provider for a specific task type.

        v8.3: Uses fallback chain — if the primary provider is unavailable
        or fails to create, tries the next provider in the fallback order.

        Returns None if no provider in the chain is available.
        """
        if not self._loaded:
            self.load()

        cache_key = task_type
        if cache_key in self._provider_cache:
            cached = self._provider_cache[cache_key]
            if cached.is_available():
                return cached
            self._provider_cache.pop(cache_key, None)

        provider_config = self._resolve_provider_config(task_type)
        if provider_config is None:
            logger.error("No provider config resolved for task '%s'", task_type)
            return None

        primary_name = provider_config.get("provider", provider_config.get("type", ""))
        provider = self._try_create_provider(provider_config, task_type, primary_name)
        if provider is not None:
            tracked = _TrackedProvider(provider, task_type, primary_name, self._usage_tracker)
            self._provider_cache[cache_key] = tracked
            return tracked

        # v8.3: Fallback chain
        fallback_used = self._try_fallback_chain(task_type, primary_name)
        if fallback_used is not None:
            fb_name, fb_provider = fallback_used
            logger.info("Using fallback provider '%s' for task '%s'", fb_name, task_type)
            tracked = _TrackedProvider(fb_provider, task_type, fb_name, self._usage_tracker)
            self._provider_cache[cache_key] = tracked
            return tracked

        logger.error("No provider available for task '%s' (all fallbacks exhausted)", task_type)
        return None

    def _try_create_provider(
        self, config: Dict[str, Any], task_type: str, provider_name: str
    ) -> Optional[LLMProvider]:
        """Try to create and validate a single provider from config."""
        provider_type = config.get("type", provider_name)
        if not validate_usage(provider_type, task_type):
            logger.error("Provider '%s' not allowed for task '%s'", provider_type, task_type)
            return None

        try:
            resolved_config = self._resolve_env_vars(config)
            provider = LLMProviderFactory.create_provider(resolved_config)
            if not provider.is_available():
                logger.warning("Provider '%s' is not available for task '%s'", provider_name, task_type)
                return None
            return provider
        except Exception as e:
            logger.error("Failed to create provider '%s' for task '%s': %s", provider_name, task_type, e)
            return None

    def _try_fallback_chain(
        self, task_type: str, excluded_name: str
    ) -> Optional[tuple]:
        """Try each fallback provider in order. Returns (name, provider) or None."""
        providers = self._providers_config.get("providers", {}).get("llm", {})

        for fb_name in _DEFAULT_FALLBACK_ORDER:
            if fb_name == excluded_name:
                continue
            if fb_name in ("default", "mock"):
                continue
            fb_config = providers.get(fb_name)
            if not fb_config:
                continue

            fb_type = fb_config.get("type", fb_name)
            if not validate_usage(fb_type, task_type):
                continue

            provider = self._try_create_provider(fb_config, task_type, fb_name)
            if provider is not None:
                return (fb_name, provider)

        return None

    def _resolve_provider_config(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Resolve provider config for a task type from routing config."""
        routing = self._routing_config.get("routing", {})
        task_routing = routing.get(task_type)
        if task_routing is None:
            task_routing = self._routing_config.get("default", {})

        provider_name = task_routing.get("provider", "")
        if not provider_name:
            return None

        providers = self._providers_config.get("providers", {}).get("llm", {})
        provider_config = providers.get(provider_name, {})

        if not provider_config:
            provider_config = {"type": provider_name}

        # Task routing overrides provider config (task-specific settings take priority)
        for key in ("model", "temperature", "max_tokens", "timeout"):
            if key in task_routing:
                provider_config[key] = task_routing[key]

        return dict(provider_config)

    @staticmethod
    def _resolve_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve api_key_env to actual api_key from environment."""
        resolved = dict(config)
        if "api_key_env" in resolved:
            env_var = resolved.pop("api_key_env")
            resolved["api_key"] = os.environ.get(env_var, "")
        return resolved

    def is_available(self, task_type: str) -> bool:
        """Check if a provider is available for a task type."""
        provider = self.get_provider(task_type)
        return provider is not None and provider.is_available()

    def get_status(self) -> Dict[str, Any]:
        """Return status of all configured providers."""
        if not self._loaded:
            self.load()

        status = {}
        providers = self._providers_config.get("providers", {}).get("llm", {})
        for name, config in providers.items():
            if name in ("default", "mock"):
                continue
            provider_type = config.get("type", name)
            try:
                resolved = self._resolve_env_vars(config)
                provider = LLMProviderFactory.create_provider(resolved)
                status[name] = {
                    "type": provider_type,
                    "model": config.get("model", ""),
                    "available": provider.is_available(),
                }
            except Exception as e:
                status[name] = {
                    "type": provider_type,
                    "model": config.get("model", ""),
                    "available": False,
                    "error": str(e),
                }
        return status

    # v8.3: Usage tracking and report

    def get_usage_summary(self) -> Dict[str, Any]:
        """Return aggregated usage statistics."""
        return self._usage_tracker.get_summary()

    def save_usage_report(self, path: str = "output/llm_usage_report.json") -> Dict[str, Any]:
        """Save usage report to JSON file and return the summary.

        v8.3: Called at pipeline end to persist LLM usage statistics.
        """
        self._usage_tracker.save(path)
        summary = self._usage_tracker.get_summary()
        summary["records"] = self._usage_tracker.to_list()
        return summary
