"""Evaluation-only Gate F V2.5 residual-remediation contract candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .core_adapter import CoreV12SemanticEvaluatorAdapter
from .models import GateIdV2
from .source_span_validation_v1 import validate_reason_span_sources_v1

V24_SOURCE_SHA256 = "aa68b62c4ca6f1df3d3073898c1010446c8ccdce151293ad62cdeea11f161bc4"
V25_ADDENDUM_SOURCE_SHA256 = "8307b1d6408c2489d15fcdb91b4ce7c41631623af315a970c1d9d238723c17e9"
GATE_F_V25_EXECUTION_SHA256 = "c6ad791171ab2d058977779f0d669906d52cf1c80c3d7c972b07b434ab507f6a"
GATE_F_V25_EVALUATOR_IDENTITY = "013aa806bc058777685665bf74d0f593de649f877deea1b4d127b85986e4b60b"


class CoreV12SemanticEvaluatorAdapterV25(CoreV12SemanticEvaluatorAdapter):
    """Compose V2.4 + V2.5 and fail closed on cross-source reason spans."""

    def __init__(self, *, project_root: Path, executor, gate_id: GateIdV2) -> None:
        if gate_id is not GateIdV2.FACTUAL_SEMANTIC:
            raise ValueError("SAV2.5 candidate is Gate-F-only")
        super().__init__(project_root=project_root, executor=executor, gate_id=gate_id)
        base = (project_root / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-prompt.txt").read_bytes()
        addendum = (project_root / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-5-addendum.txt").read_bytes()
        if hashlib.sha256(base).hexdigest() != V24_SOURCE_SHA256:
            raise RuntimeError("SAV2.5 base prompt identity drift")
        if hashlib.sha256(addendum).hexdigest() != V25_ADDENDUM_SOURCE_SHA256:
            raise RuntimeError("SAV2.5 addendum identity drift")
        if not base.endswith(b"\n") or base.endswith(b"\n\n") or not addendum.endswith(b"\n") or addendum.endswith(b"\n\n"):
            raise RuntimeError("SAV2.5 prompt padding drift")
        base_text = base[:-1].decode("utf-8", errors="strict")
        addendum_text = addendum[:-1].decode("utf-8", errors="strict")
        marker = "\nFACTUAL SUMMARY:"
        if base_text.count(marker) != 1:
            raise RuntimeError("SAV2.5 composition marker drift")
        execution = base_text.replace(marker, f"\n{addendum_text}\n\nFACTUAL SUMMARY:")
        if hashlib.sha256(execution.encode()).hexdigest() != GATE_F_V25_EXECUTION_SHA256:
            raise RuntimeError("SAV2.5 executable prompt identity drift")
        self._template = execution
        self.prompt_identity = "sha256:" + GATE_F_V25_EXECUTION_SHA256
        self.evaluator_identity = GATE_F_V25_EVALUATOR_IDENTITY

    def __call__(self, request: dict[str, object]) -> str:
        raw = super().__call__(request)
        factual_summary, candidate = request.get("factual_summary"), request.get("candidate")
        if type(factual_summary) is not str or type(candidate) is not str:
            raise ValueError("SAV2.5 source text unavailable for span validation")
        validate_reason_span_sources_v1(raw_response=raw, factual_summary=factual_summary, candidate=candidate)
        return raw


__all__ = (
    "CoreV12SemanticEvaluatorAdapterV25",
    "GATE_F_V25_EVALUATOR_IDENTITY",
    "GATE_F_V25_EXECUTION_SHA256",
    "V24_SOURCE_SHA256",
    "V25_ADDENDUM_SOURCE_SHA256",
)
