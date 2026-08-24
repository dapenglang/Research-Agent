"""
Unified LLM Provider interface for Research Agent v7.

Provides four provider types:
  1. OpenAIProvider    — real OpenAI API calls (uses the ``openai`` package)
  2. DeepSeekProvider  — real DeepSeek API calls (OpenAI-compatible)
  3. LocalLLMProvider  — real HTTP calls to a local LLM endpoint (vLLM, Ollama)
  4. MockProvider      — template-based mock for tests/dev ONLY

Usage validation:
  MockProvider is allowed ONLY for: unit_test, integration_test, development
  MockProvider is PROHIBITED for:
    literature_analysis, innovation_generation, paper_generation,
    experiment_analysis

Use ``validate_usage(provider_name, task_type)`` to check before dispatching.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# Usage policy: Mock is only for dev/test scenarios
# ============================================================

# Tasks where Mock provider is ALLOWED
_MOCK_ALLOWED_TASKS: frozenset[str] = frozenset({
    "unit_test",
    "integration_test",
    "development",
})

# Tasks where Mock provider is PROHIBITED
_MOCK_PROHIBITED_TASKS: frozenset[str] = frozenset({
    "literature_analysis",
    "innovation_generation",
    "paper_generation",
    "experiment_analysis",
})


def validate_usage(provider_name: str, task_type: str) -> bool:
    """
    Check whether a provider is allowed for a given task type.

    The Mock provider is the only one with restrictions:
      - Allowed for: unit_test, integration_test, development
      - Prohibited for: literature_analysis, innovation_generation,
                        paper_generation, experiment_analysis

    Args:
        provider_name: Name of the provider (e.g. "openai", "local", "mock").
        task_type:     The task type string to validate against.

    Returns:
        True if the provider is permitted for the task type, False otherwise.
    """
    name_lower = provider_name.lower()

    if name_lower == "mock":
        if task_type in _MOCK_PROHIBITED_TASKS:
            logger.error(
                "Mock provider is PROHIBITED for task '%s'. "
                "Use a real provider (openai/local) for production tasks.",
                task_type,
            )
            return False
        if task_type not in _MOCK_ALLOWED_TASKS:
            logger.warning(
                "Mock provider used for unrecognised task '%s'. "
                "Allowed tasks: %s",
                task_type, sorted(_MOCK_ALLOWED_TASKS),
            )
            return False
        return True

    # OpenAI and Local providers are allowed for all task types
    return True


# ============================================================
# Abstract base class
# ============================================================

class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Subclasses must implement:
      - generate(prompt, **kwargs) -> str
      - is_available() -> bool
      - get_name() -> str
    """

    def __init__(
        self,
        model_name: str = "default",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        """
        Initialize the provider.

        Args:
            model_name:  Model identifier string.
            temperature: Sampling temperature (0.0–1.0).
            max_tokens:  Maximum tokens to generate per call.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._available: bool = True

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt string.
            **kwargs: Additional provider-specific options (e.g. context,
                      system_message, stop_sequences).

        Returns:
            The generated text response.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is ready to serve requests."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return the provider's display name."""
        ...

    def get_info(self) -> Dict[str, Any]:
        """Return a dictionary of provider configuration info."""
        return {
            "provider_type": self.__class__.__name__,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "available": self._available,
        }


# ============================================================
# OpenAI Provider — real API calls
# ============================================================

class OpenAIProvider(LLMProvider):
    """
    Real OpenAI API provider.

    Uses the ``openai`` Python package. The API key is read from the
    ``OPENAI_API_KEY`` environment variable if not passed explicitly.

    Supports OpenAI-compatible endpoints via ``base_url`` (Azure,
    third-party proxies, etc.).
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(model_name, temperature, max_tokens)

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "")
        self._client = None  # lazy init

        if not self.api_key:
            logger.warning(
                "OpenAI API key not configured (OPENAI_API_KEY env var empty). "
                "Provider marked as unavailable."
            )
            self._available = False
        else:
            self._available = True

    def _get_client(self):
        """Lazily initialise the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                self._client = OpenAI(**client_kwargs)
                logger.info("OpenAI client initialised (model=%s)", self.model_name)
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                self._available = False
                raise ImportError("openai package is not installed")
        return self._client

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Call the OpenAI Chat Completions API.

        Args:
            prompt: User prompt text.
            **kwargs: Optional keys:
                context (str):         Additional context prepended as a
                                      system message.
                system_message (str):  Custom system message.
                temperature (float):   Override per-call temperature.
                max_tokens (int):      Override per-call max tokens.
                stop (list[str]):      Stop sequences.

        Returns:
            Generated text from the API.

        Raises:
            RuntimeError: If the provider is unavailable or the API call fails.
        """
        if not self._available:
            raise RuntimeError("OpenAI provider unavailable: API key not configured")

        try:
            client = self._get_client()

            context = kwargs.get("context", "")
            system_message = kwargs.get("system_message")
            call_temp = kwargs.get("temperature", self.temperature)
            call_max_tokens = kwargs.get("max_tokens", self.max_tokens)
            stop = kwargs.get("stop")

            messages: List[Dict[str, str]] = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            elif context:
                messages.append({
                    "role": "system",
                    "content": (
                        "You are a scientific research assistant. "
                        f"Use the following context:\n\n{context}"
                    ),
                })
            else:
                messages.append({
                    "role": "system",
                    "content": (
                        "You are a scientific research assistant specialized "
                        "in analyzing academic papers."
                    ),
                })
            messages.append({"role": "user", "content": prompt})

            logger.info("Calling OpenAI API (model=%s)...", self.model_name)
            create_kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": call_temp,
                "max_tokens": call_max_tokens,
            }
            if stop:
                create_kwargs["stop"] = stop

            response = client.chat.completions.create(**create_kwargs)
            result = response.choices[0].message.content or ""
            logger.info("OpenAI API call succeeded, %d chars generated", len(result))
            return result

        except Exception as e:
            logger.error("OpenAI API call failed: %s", str(e), exc_info=True)
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

    def is_available(self) -> bool:
        return self._available

    def get_name(self) -> str:
        return f"OpenAIProvider(model={self.model_name})"


# ============================================================
# DeepSeek Provider — real API calls (OpenAI-compatible)
# ============================================================

class DeepSeekProvider(LLMProvider):
    """
    Real DeepSeek API provider.

    Uses the ``openai`` Python package with DeepSeek's OpenAI-compatible
    endpoint (https://api.deepseek.com/v1). Supports deepseek-chat and
    deepseek-reasoner models.

    The API key is read from the ``DEEPSEEK_API_KEY`` environment variable
    if not passed explicitly.
    """

    DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(
        self,
        model_name: str = "deepseek-chat",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(model_name, temperature, max_tokens)

        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or self.DEEPSEEK_BASE_URL
        self._client = None

        if not self.api_key:
            logger.warning(
                "DeepSeek API key not configured (DEEPSEEK_API_KEY env var empty). "
                "Provider marked as unavailable."
            )
            self._available = False
        else:
            self._available = True

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                logger.info("DeepSeek client initialised (model=%s)", self.model_name)
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                self._available = False
                raise ImportError("openai package is not installed")
        return self._client

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self._available:
            raise RuntimeError("DeepSeek provider unavailable: API key not configured")

        try:
            client = self._get_client()

            system_message = kwargs.get("system_message", "You are a scientific research assistant.")
            context = kwargs.get("context", "")
            call_temp = kwargs.get("temperature", self.temperature)
            call_max_tokens = kwargs.get("max_tokens", self.max_tokens)

            messages: List[Dict[str, str]] = []
            if context:
                messages.append({"role": "system", "content": f"{system_message}\n\nContext:\n{context}"})
            else:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            logger.info("Calling DeepSeek API (model=%s)...", self.model_name)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=call_temp,
                max_tokens=call_max_tokens,
            )
            result = response.choices[0].message.content or ""
            logger.info("DeepSeek API call succeeded, %d chars generated", len(result))
            return result

        except Exception as e:
            logger.error("DeepSeek API call failed: %s", str(e), exc_info=True)
            raise RuntimeError(f"DeepSeek API call failed: {e}") from e

    def is_available(self) -> bool:
        return self._available

    def get_name(self) -> str:
        return f"DeepSeekProvider(model={self.model_name})"


# ============================================================
# Local LLM Provider — real HTTP calls
# ============================================================

class LocalLLMProvider(LLMProvider):
    """
    Real local LLM provider via HTTP.

    Supports OpenAI-compatible local endpoints (vLLM, Ollama, llama.cpp
    server, etc.). Sends POST requests to ``{endpoint}/completions``
    (or ``{endpoint}/chat/completions`` if ``chat_mode`` is True).
    """

    def __init__(
        self,
        model_name: str = "local-llm",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        endpoint: Optional[str] = None,
        chat_mode: bool = False,
        timeout: int = 120,
    ) -> None:
        super().__init__(model_name, temperature, max_tokens)

        self.endpoint = endpoint or os.environ.get("LOCAL_LLM_ENDPOINT", "")
        self.chat_mode = chat_mode
        self.timeout = timeout

        if not self.endpoint:
            logger.warning(
                "Local LLM endpoint not configured (LOCAL_LLM_ENDPOINT env empty). "
                "Provider marked as unavailable."
            )
            self._available = False
        else:
            self._available = True

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Call the local LLM endpoint via HTTP POST.

        Args:
            prompt: Input prompt text.
            **kwargs: Optional keys:
                context (str):       Context to prepend.
                temperature (float): Override per-call temperature.
                max_tokens (int):    Override per-call max tokens.
                stop (list[str]):    Stop sequences.

        Returns:
            Generated text from the local model.

        Raises:
            RuntimeError: If endpoint is not configured or the HTTP call fails.
        """
        if not self._available:
            raise RuntimeError("Local LLM provider unavailable: endpoint not configured")

        try:
            import requests  # type: ignore[import-untyped]

            context = kwargs.get("context", "")
            call_temp = kwargs.get("temperature", self.temperature)
            call_max_tokens = kwargs.get("max_tokens", self.max_tokens)
            stop = kwargs.get("stop")

            logger.info("Calling local LLM (endpoint=%s)...", self.endpoint)

            if self.chat_mode:
                messages: List[Dict[str, str]] = []
                if context:
                    messages.append({"role": "system", "content": context})
                messages.append({"role": "user", "content": prompt})

                payload: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": call_temp,
                    "max_tokens": call_max_tokens,
                }
                if stop:
                    payload["stop"] = stop

                url = f"{self.endpoint}/chat/completions"
                resp = requests.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                full_prompt = f"Context:\n{context}\n\nPrompt:\n{prompt}" if context else prompt

                payload = {
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "temperature": call_temp,
                    "max_tokens": call_max_tokens,
                }
                if stop:
                    payload["stop"] = stop

                url = f"{self.endpoint}/completions"
                resp = requests.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                result = data.get("choices", [{}])[0].get("text", "")

            logger.info("Local LLM call succeeded, %d chars generated", len(result))
            return result

        except ImportError:
            logger.error("requests package not installed. Run: pip install requests")
            raise RuntimeError("requests package is not installed")
        except Exception as e:
            logger.error("Local LLM call failed: %s", str(e), exc_info=True)
            raise RuntimeError(f"Local LLM call failed: {e}") from e

    def is_available(self) -> bool:
        return self._available

    def get_name(self) -> str:
        return f"LocalLLMProvider(model={self.model_name}, endpoint={self.endpoint})"


# ============================================================
# Mock Provider — for tests/dev ONLY
# ============================================================

class MockProvider(LLMProvider):
    """
    Template-based mock LLM provider for tests and development.

    IMPORTANT: This provider does NOT call any real API. It returns
    pre-defined responses based on keyword matching in the prompt.
    It is strictly for unit_test, integration_test, and development
    scenarios. Using it for literature_analysis, innovation_generation,
    paper_generation, or experiment_analysis is prohibited — use
    ``validate_usage("mock", task_type)`` to enforce this.
    """

    MOCK_RESPONSES: Dict[str, str] = {
        "gap_analysis": (
            "## LLM Analysis (Mock)\n\n"
            "### Research Clusters\n"
            "Current papers focus on VLM safety, including:\n"
            "1. Multilingual safety alignment\n"
            "2. Vision encoder safety pre-training\n"
            "3. Safety-critical event understanding\n\n"
            "### Technical Evolution\n"
            "Keyword filtering -> Safety classifiers -> Multimodal alignment\n\n"
            "### Future Opportunities\n"
            "1. Unified cross-modal defense framework\n"
            "2. Provable safety alignment guarantees\n"
            "3. Efficient safety fine-tuning methods\n"
        ),
        "hypothesis": (
            "### Hypothesis (Mock)\n\n"
            "H_1: A unified cross-modal safety defense framework can\n"
            "simultaneously defend against text and image attacks.\n\n"
            "Formulation: min_f E[max(0, L_safe(f(x_t, x_v)) - margin)]\n"
        ),
        "method": (
            "### Method Overview (Mock)\n\n"
            "Propose UniSafe: Unified Cross-modal Safety Defense\n\n"
            "Architecture:\n"
            "1. Text safety encoder\n"
            "2. Visual safety encoder\n"
            "3. Cross-modal fusion layer\n"
            "4. Safety classification head\n"
        ),
        "experiment": (
            "### Experiment Design (Mock)\n\n"
            "Datasets: MM-SafetyBench, AdvBench, VLGuard\n"
            "Models: LLaVA-1.5-7B, Qwen-VL-Chat\n"
            "Metrics: ASR, FPR, Safety Score\n"
        ),
        "default": (
            "[Mock LLM Response]\n"
            "This response was generated by MockProvider for testing.\n"
            "Replace with a real provider (OpenAI/Local) for production use.\n"
        ),
    }

    def __init__(
        self,
        model_name: str = "mock-llm",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(model_name, temperature, max_tokens)
        self._available = True
        logger.info("MockProvider initialised (for tests/dev only)")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        Return a mock response based on keyword matching.

        Args:
            prompt: Input prompt (used for keyword matching only).
            **kwargs: Ignored (temperature, max_tokens have no effect).

        Returns:
            A pre-defined mock response string.
        """
        prompt_lower = prompt.lower()

        if "gap" in prompt_lower or "research gap" in prompt_lower or "blank" in prompt_lower:
            key = "gap_analysis"
        elif "hypothesis" in prompt_lower or "assumption" in prompt_lower:
            key = "hypothesis"
        elif "method" in prompt_lower:
            key = "method"
        elif "experiment" in prompt_lower:
            key = "experiment"
        else:
            key = "default"

        result = self.MOCK_RESPONSES.get(key, self.MOCK_RESPONSES["default"])
        logger.info("MockProvider returned response (key=%s)", key)
        return result

    def is_available(self) -> bool:
        return True

    def get_name(self) -> str:
        return f"MockProvider(model={self.model_name})"


# ============================================================
# Provider Factory
# ============================================================

class LLMProviderFactory:
    """
    Factory for creating LLM providers from configuration dictionaries.

    Supported config ``type`` values:
      - "openai":    OpenAIProvider
      - "deepseek":  DeepSeekProvider
      - "local":     LocalLLMProvider (supports vllm/ollama backends)
      - "ollama":    LocalLLMProvider (Ollama OpenAI-compatible endpoint)
      - "mock":      MockProvider (dev/test only)

    Usage:
        provider = LLMProviderFactory.create_provider({
            "type": "openai",
            "model_name": "gpt-4",
            "api_key": "sk-...",
        })
    """

    @staticmethod
    def create_provider(config: Dict[str, Any]) -> LLMProvider:
        """
        Create an LLM provider from a config dictionary.

        Args:
            config: Provider configuration. Must contain a ``type`` key.
                    Additional keys are passed to the provider constructor.
                    For "local" type, ``backend`` can be "vllm" or "ollama".

        Returns:
            An LLMProvider instance.

        Raises:
            ValueError: If the provider type is unknown.
        """
        provider_type = config.get("type", "mock").lower()

        if provider_type == "openai":
            return OpenAIProvider(
                model_name=config.get("model_name", config.get("model", "gpt-4")),
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
                api_key=config.get("api_key"),
                base_url=config.get("base_url", config.get("endpoint")),
            )
        elif provider_type == "deepseek":
            return DeepSeekProvider(
                model_name=config.get("model_name", config.get("model", "deepseek-chat")),
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
                api_key=config.get("api_key"),
                base_url=config.get("base_url", config.get("endpoint")),
            )
        elif provider_type == "local":
            backend = config.get("backend", "")
            model_path = config.get("model_path", config.get("local_path", ""))
            endpoint = config.get("endpoint", "")

            if backend == "vllm" and not endpoint:
                endpoint = "http://localhost:8000/v1"
            elif backend == "ollama" and not endpoint:
                endpoint = "http://localhost:11434/v1"

            model_name = config.get("model_name", config.get("model", ""))
            if not model_name and model_path:
                model_name = os.path.basename(model_path)

            return LocalLLMProvider(
                model_name=model_name or "local-llm",
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
                endpoint=endpoint,
                chat_mode=True,
                timeout=config.get("timeout", 120),
            )
        elif provider_type == "ollama":
            endpoint = config.get("endpoint", "http://localhost:11434/v1")
            model_name = config.get("model_name", config.get("model", "llama2"))
            return LocalLLMProvider(
                model_name=model_name,
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
                endpoint=endpoint,
                chat_mode=True,
                timeout=config.get("timeout", 120),
            )
        elif provider_type == "mock":
            return MockProvider(
                model_name=config.get("model_name", "mock-llm"),
                temperature=config.get("temperature", 0.3),
                max_tokens=config.get("max_tokens", 4096),
            )
        else:
            raise ValueError(
                f"Unknown provider type: '{provider_type}'. "
                f"Supported types: openai, deepseek, local, ollama, mock"
            )


# ============================================================
# Logging Proxy — wraps a provider and records all calls
# ============================================================

class LLMLoggingProxy(LLMProvider):
    """Wraps an LLMProvider and logs every generate() call to a JSON file."""

    _log_entries: list = []

    def __init__(self, inner: LLMProvider, module_id: str = "", log_path: str = "") -> None:
        super().__init__(inner.model_name, inner.temperature, inner.max_tokens)
        self._inner = inner
        self._module_id = module_id
        self._log_path = log_path
        self._is_mock = isinstance(inner, MockProvider)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        import time
        entry = {
            "module": self._module_id,
            "provider": self._inner.__class__.__name__,
            "model": self._inner.model_name,
            "is_mock": self._is_mock,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "fallback": "mock_template" if self._is_mock else "none",
        }
        try:
            result = self._inner.generate(prompt, **kwargs)
            entry["status"] = "success"
            entry["response_length"] = len(result)
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            self._write_log(entry)
            raise
        self._write_log(entry)
        return result

    def _write_log(self, entry: dict) -> None:
        self._log_entries.append(entry)
        if self._log_path:
            import json
            from pathlib import Path
            log_file = Path(self._log_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(self._log_entries, f, ensure_ascii=False, indent=2)

    def is_available(self) -> bool:
        return self._inner.is_available()

    def get_name(self) -> str:
        return f"LLMLoggingProxy({self._inner.get_name()})"

    @classmethod
    def get_log_entries(cls) -> list:
        return cls._log_entries

    @classmethod
    def has_mock_calls(cls) -> bool:
        return any(e.get("is_mock") for e in cls._log_entries)
