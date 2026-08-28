"""Module 10 — Scientific Result Analysis.

Analyzes experiment results from synthetic (Module 08) and real (Module 09)
experiment engines. Preserves data_origin. Produces decision routing signal.
"""

from .interface import ResultAnalysisInput, ResultAnalysisOutput, Module10Interface

__all__ = [
    "ResultAnalysisInput",
    "ResultAnalysisOutput",
    "Module10Interface",
]
