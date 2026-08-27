"""Evaluation-only Semantic Admission V2 contracts.

The public API is lazy so lightweight constrained-runner modules do not import
host application dependencies inside the isolated WSL model environment.
"""
from __future__ import annotations

from importlib import import_module

__all__ = (
    "AdmissionInputV2", "AdmissionReceiptV2", "AuthorityBindingV2",
    "CandidateBindingV2", "FinalAdmissionDecisionV2", "GateDecisionV2",
    "GateIdV2", "PortabilityControlV2", "ReasonRecordV2", "ReasonStatusV2",
    "RuntimeBindingV2", "SemanticAdmissionCoordinatorV2", "SurfaceDefenseFindingV2",
    "CoreV12SemanticEvaluatorAdapter",
)

_PUBLIC_MODULES = {
    "SemanticAdmissionCoordinatorV2": ".coordinator",
    "CoreV12SemanticEvaluatorAdapter": ".core_adapter",
    **{name: ".models" for name in __all__ if name not in {
        "SemanticAdmissionCoordinatorV2", "CoreV12SemanticEvaluatorAdapter"}},
}


def __getattr__(name: str):
    module_name = _PUBLIC_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
