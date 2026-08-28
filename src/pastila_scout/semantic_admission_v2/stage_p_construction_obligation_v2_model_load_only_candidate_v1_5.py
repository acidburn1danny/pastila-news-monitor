"""Injection-only V1.5 model-load candidate; contains no runtime load implementation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from .stage_p_construction_obligation_v2_model_load_authority_contract_v1 import (
    PreloadEnvironmentV1, parse_load_only_authority_v1,
    validate_preload_environment_v1,
)
from .stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    canonical_observed_model_load_policy_v1, validate_model_load_policy_gate_v1,
)


LOAD_ONLY_CANDIDATE_IDENTITY = "0c75989a971d7170d7cd01b351b736a0664c5ee1516d5c612f8ee82150f0940c"


@dataclass(frozen=True, slots=True)
class InjectedLoadOperationsV1:
    load_base_nf4: Callable[[], object]
    attach_adapter: Callable[[object], object]
    cleanup: Callable[[object], None]


@dataclass(frozen=True, slots=True)
class LoadOnlyCandidateResultV1_5:
    status: str
    receipts: tuple[bytes, ...]


def execute_injected_load_only_candidate_v1_5(
    *, raw_policy_receipt: bytes, raw_authority_receipt: bytes,
    environment: PreloadEnvironmentV1, operations: InjectedLoadOperationsV1,
) -> LoadOnlyCandidateResultV1_5:
    """Exercise one injected load attempt and always release acquired resources."""
    if type(operations) is not InjectedLoadOperationsV1:
        raise TypeError("MODEL_LOAD_OPERATIONS_EXACT_TYPE_REQUIRED")
    expected_policy = validate_model_load_policy_gate_v1(
        observed=canonical_observed_model_load_policy_v1())
    if raw_policy_receipt != expected_policy:
        raise ValueError("MODEL_LOAD_POLICY_RECEIPT_MISMATCH")
    authority = parse_load_only_authority_v1(
        raw_receipt=raw_authority_receipt,
        expected_load_candidate_identity=LOAD_ONLY_CANDIDATE_IDENTITY)
    validate_preload_environment_v1(observed=environment, authority=authority)

    receipts: list[bytes] = [_receipt("MODEL_LOAD_STARTED", authority, None)]
    resource = None
    try:
        resource = operations.load_base_nf4()
        if resource is None:
            raise RuntimeError("MODEL_LOAD_BASE_RESOURCE_MISSING")
        adapted = operations.attach_adapter(resource)
        if adapted is None:
            raise RuntimeError("MODEL_LOAD_ADAPTER_RESOURCE_MISSING")
        resource = adapted
        receipts.append(_receipt("MODEL_LOAD_COMPLETED", authority, None))
        status = "LOAD_ONLY_COMPLETED_AND_RELEASED"
    except Exception as exc:
        receipts.append(_receipt("MODEL_LOAD_FAILED", authority, type(exc).__name__))
        status = "LOAD_ONLY_FAILED_AND_RELEASED"
    finally:
        if resource is not None:
            try:
                operations.cleanup(resource)
                receipts.append(_receipt("MODEL_LOAD_CLEANUP_COMPLETED", authority, None))
            except Exception as cleanup_exc:
                receipts.append(_receipt(
                    "MODEL_LOAD_CLEANUP_FAILED", authority, type(cleanup_exc).__name__))
                status = "LOAD_ONLY_CLEANUP_FAILED"
    return LoadOnlyCandidateResultV1_5(status, tuple(receipts))


def _receipt(event: str, authority: object, failure_type: str | None) -> bytes:
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-model-load-only-event",
        "schema_version": "1.5.0", "load_candidate_identity": LOAD_ONLY_CANDIDATE_IDENTITY,
        "authority_receipt_identity": authority.authority_receipt_identity,
        "event": event, "failure_type": failure_type, "event_identity": "",
    }
    value["event_identity"] = hashlib.sha256(_canonical(
        {k: v for k, v in value.items() if k != "event_identity"})).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "InjectedLoadOperationsV1", "LOAD_ONLY_CANDIDATE_IDENTITY",
    "LoadOnlyCandidateResultV1_5", "execute_injected_load_only_candidate_v1_5",
)
