"""
Method Backend Interface

Abstract interface for experiment method backends.
SAMRA is one implementation of this interface.
New research methods implement this interface to plug into
Module 08 (Synthetic) and Module 09 (Real) experiment engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class MethodSpec:
    """Method specification loaded from method_spec.json."""
    method_name: str
    components: Dict[str, Any]
    variables: Dict[str, Any]
    parameters: Dict[str, Any]
    architecture: Dict[str, Any]
    relations: Dict[str, Any]


@dataclass
class ExperimentResult:
    """Result from a single experiment run."""
    experiment_id: str
    metrics: Dict[str, float]
    raw_data: Dict[str, Any]
    data_origin: str  # "synthetic" or "real"
    seed: int
    config: Dict[str, Any]


class MethodBackend(ABC):
    """
    Abstract interface for experiment method backends.

    A method backend provides:
    - Synthetic experiment execution (for Module 08)
    - Real experiment execution (for Module 09, if applicable)
    - Metric computation
    - State extraction (for real models)

    SAMRA is one implementation. New research methods create
    their own implementation and register it.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Unique name for this backend (e.g., 'samra', 'contrastive_loss')."""
        ...

    @abstractmethod
    def load_spec(self, method_spec: Dict[str, Any]) -> MethodSpec:
        """Load and validate method specification."""
        ...

    @abstractmethod
    def run_synthetic_experiment(
        self,
        spec: MethodSpec,
        experiment_config: Dict[str, Any],
        seed: int = 42,
    ) -> ExperimentResult:
        """Run a synthetic experiment based on the method spec."""
        ...

    def run_real_experiment(
        self,
        spec: MethodSpec,
        experiment_config: Dict[str, Any],
        model_handler: Any,
        seed: int = 42,
    ) -> ExperimentResult:
        """
        Run a real experiment using an actual model.

        Default: NotSupported. Override if the method supports real experiments.
        """
        raise NotImplementedError(
            f"Backend '{self.backend_name}' does not support real experiments"
        )

    @abstractmethod
    def get_required_metrics(self) -> List[str]:
        """Return the list of metrics this backend produces."""
        ...

    @abstractmethod
    def get_method_components(self) -> List[str]:
        """Return the list of method components (e.g., ['injector', 'projector', 'estimator'])."""
        ...


class BackendRegistry:
    """Registry for method backends. SAMRA registers itself; new methods register theirs."""

    def __init__(self):
        self._backends: Dict[str, type] = {}

    def register(self, name: str, backend_class: type) -> None:
        if not issubclass(backend_class, MethodBackend):
            raise ValueError(f"{backend_class} must inherit from MethodBackend")
        self._backends[name] = backend_class

    def get(self, name: str) -> MethodBackend:
        if name not in self._backends:
            raise KeyError(
                f"Method backend '{name}' not registered. "
                f"Available: {list(self._backends.keys())}"
            )
        return self._backends[name]()

    def list_available(self) -> List[str]:
        return list(self._backends.keys())


backend_registry = BackendRegistry()
