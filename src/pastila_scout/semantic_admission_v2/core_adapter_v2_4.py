"""Evaluation-only Gate F V2.4 proposition-and-scope contract candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .core_adapter import CoreV12SemanticEvaluatorAdapter
from .models import GateIdV2

GATE_F_V24_SOURCE_SHA256 = "aa68b62c4ca6f1df3d3073898c1010446c8ccdce151293ad62cdeea11f161bc4"
GATE_F_V24_EXECUTION_SHA256 = "aed34f51c1c56c53b01347074daae234271b820fe35abc20db2d4af9618f0861"
GATE_F_V24_EVALUATOR_IDENTITY = "abc7441d98b387d76de3b176068a4a93235f0f46be6dad30b7873dc0e26b1bba"


class CoreV12SemanticEvaluatorAdapterV24(CoreV12SemanticEvaluatorAdapter):
    """Render V2.4 without changing execution, parsing, or factual authority."""

    def __init__(self, *, project_root: Path, executor, gate_id: GateIdV2) -> None:
        if gate_id is not GateIdV2.FACTUAL_SEMANTIC:
            raise ValueError("SAV2.4 candidate is Gate-F-only")
        super().__init__(project_root=project_root, executor=executor, gate_id=gate_id)
        data = (project_root / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-prompt.txt").read_bytes()
        if hashlib.sha256(data).hexdigest() != GATE_F_V24_SOURCE_SHA256:
            raise RuntimeError("SAV2.4 source prompt identity drift")
        if not data.endswith(b"\n") or data.endswith(b"\n\n"):
            raise RuntimeError("SAV2.4 source prompt padding drift")
        execution = data[:-1]
        if hashlib.sha256(execution).hexdigest() != GATE_F_V24_EXECUTION_SHA256:
            raise RuntimeError("SAV2.4 executable prompt identity drift")
        self._template = execution.decode("utf-8", errors="strict")
        self.prompt_identity = "sha256:" + GATE_F_V24_EXECUTION_SHA256
        self.evaluator_identity = GATE_F_V24_EVALUATOR_IDENTITY


__all__ = (
    "CoreV12SemanticEvaluatorAdapterV24",
    "GATE_F_V24_EVALUATOR_IDENTITY",
    "GATE_F_V24_EXECUTION_SHA256",
    "GATE_F_V24_SOURCE_SHA256",
)
