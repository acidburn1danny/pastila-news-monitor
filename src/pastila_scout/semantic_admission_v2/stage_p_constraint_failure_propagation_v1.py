"""Evaluation-only propagation of validated durable constraint-liveness receipts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2, ProviderExecutionResultV2

from .stage_p_scope_graph_durable_executor_v1_2 import (
    ConstraintLivenessExecutionReceiptV1, read_constraint_liveness_failure_v1,
)


def validate_constraint_liveness_root_v1(root: Path) -> ConstraintLivenessExecutionReceiptV1 | None:
    """Return a receipt only when runner and host durable records agree exactly."""
    if not root.is_dir():
        return None
    receipt = read_constraint_liveness_failure_v1(root)
    host_paths = sorted(root.glob("host-*-host-constraint-liveness-failure-classified.json"))
    if receipt is None:
        if host_paths:
            raise ValueError("HOST_LIVENESS_WITHOUT_RUNNER_RECEIPT")
        return None
    if len(host_paths) != 1:
        raise ValueError("LIVENESS_HOST_RECEIPT_CARDINALITY_INVALID")
    host = json.loads(host_paths[0].read_bytes())
    expected = receipt.as_json_value()
    observed = {key: host.get(key) for key in expected}
    if observed != expected or host.get("event") != "HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED":
        raise ValueError("LIVENESS_RUNNER_HOST_MISMATCH")
    return receipt


def recover_constraint_liveness_v1(*, result: ProviderExecutionResultV2,
                                   durable_lifecycle_root: Path) -> ConstraintLivenessExecutionReceiptV1 | None:
    """Recover a known typed failure; unknown/generic failures remain unclassified."""
    if type(result) is not ProviderExecutionResultV2:
        raise TypeError("exact provider execution result required")
    if result.outcome is not ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE:
        return None
    digest = hashlib.sha256(result.request_id.encode()).hexdigest()
    return validate_constraint_liveness_root_v1(durable_lifecycle_root / digest)


__all__ = ("recover_constraint_liveness_v1", "validate_constraint_liveness_root_v1")
