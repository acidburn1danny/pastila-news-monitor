"""V1.2.1 Linux composition with early bound failure evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    DURABLE_FILESYSTEM_SINK_IDENTITY, SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1,
    DurableArtifactReceiptV1, DurableEvidenceRootBindingV1,
    create_durable_filesystem_sink_v1_2_1,
)
from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import parse_generation_authority_v1_2_1
from .stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2_1 import LINUX_CHILD_PROCESS_ADAPTER_IDENTITY, build_linux_child_process_operations_v1_2_1
from .stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 import SUPERVISOR_CANDIDATE_IDENTITY, InjectedDurableSinkV1, LinuxGenerationSupervisorOutcomeV1, supervise_linux_generation_candidate_v1_2_1
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import parse_runner_request_v1

LINUX_GENERATION_COMPOSITION_IDENTITY_FIELDS = (
    "construction-obligation-v2-linux-generation-composition-v1.2.1",
    "child-adapter:" + LINUX_CHILD_PROCESS_ADAPTER_IDENTITY,
    "supervisor:" + SUPERVISOR_CANDIDATE_IDENTITY,
    "durable-sink:" + DURABLE_FILESYSTEM_SINK_IDENTITY,
    "durable-supervisor-admission:" + SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1,
    "bound-pre-model-failure-receipt:required",
)
LINUX_GENERATION_COMPOSITION_IDENTITY = hashlib.sha256(
    "\n".join(LINUX_GENERATION_COMPOSITION_IDENTITY_FIELDS).encode()
).hexdigest()


@dataclass(frozen=True, slots=True)
class LinuxGenerationCompositionOutcomeV1_2:
    composition_identity: str
    sink_instance_identity: str
    supervisor_outcome: LinuxGenerationSupervisorOutcomeV1
    durable_receipts: tuple[DurableArtifactReceiptV1, ...]


def run_linux_generation_composition_v1_2_1(
    *, raw_policy_receipt: bytes, raw_authority_receipt: bytes,
    raw_runner_request: bytes, system_prompt: str, evidence_root: Path,
    timeout_seconds: float, context_factory=None,
) -> LinuxGenerationCompositionOutcomeV1_2:
    request = parse_runner_request_v1(raw_request=raw_runner_request)
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=raw_authority_receipt,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(raw_runner_request).hexdigest(),
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    sink = create_durable_filesystem_sink_v1_2_1(
        root=evidence_root,
        binding=DurableEvidenceRootBindingV1(
            request.provider_request_id, request.source_context_identity,
            authority.authority_receipt_identity, SUPERVISOR_CANDIDATE_IDENTITY,
        ),
    )
    receipts: list[DurableArtifactReceiptV1] = []

    def persist(label: str, raw: bytes) -> None:
        receipt = sink.persist(label, raw)
        if type(receipt) is not DurableArtifactReceiptV1:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_COMPOSITION_DURABLE_RECEIPT_EXACT_TYPE_REQUIRED")
        if receipt.sink_instance_identity != sink.sink_instance_identity:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_COMPOSITION_SINK_IDENTITY_MISMATCH")
        receipts.append(receipt)

    try:
        child = build_linux_child_process_operations_v1_2_1(
            raw_policy_receipt=raw_policy_receipt,
            raw_authority_receipt=raw_authority_receipt,
            context_factory=context_factory,
        )
        outcome = supervise_linux_generation_candidate_v1_2_1(
            raw_policy_receipt=raw_policy_receipt,
            raw_authority_receipt=raw_authority_receipt,
            raw_runner_request=raw_runner_request,
            system_prompt=system_prompt,
            timeout_seconds=timeout_seconds,
            child_operations=child,
            durable_sink=InjectedDurableSinkV1(persist),
        )
    except Exception as exc:
        persist("composition-pre-model-failure-v1-2.json", _failure(exc, authority.authority_receipt_identity))
        raise
    hashes = tuple((item.label, item.sha256) for item in receipts)
    if hashes != outcome.persisted_artifact_sha256:
        raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_COMPOSITION_DURABLE_RECONCILIATION_FAILED")
    return LinuxGenerationCompositionOutcomeV1_2(
        LINUX_GENERATION_COMPOSITION_IDENTITY, sink.sink_instance_identity,
        outcome, tuple(receipts),
    )


def _failure(exc: Exception, authority_identity: str) -> bytes:
    value = {
        "schema_name": "pastila-construction-obligation-v2-composition-pre-model-failure",
        "schema_version": "1.2.1",
        "composition_identity": LINUX_GENERATION_COMPOSITION_IDENTITY,
        "authority_receipt_identity": authority_identity,
        "failure_type": type(exc).__name__,
        "model_load_started": False,
        "generation_started": False,
        "retry_count": 0,
        "receipt_identity": "",
    }
    canonical = lambda item: (json.dumps(item, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    value["receipt_identity"] = hashlib.sha256(canonical({k: v for k, v in value.items() if k != "receipt_identity"})).hexdigest()
    return canonical(value)


__all__ = (
    "LINUX_GENERATION_COMPOSITION_IDENTITY",
    "LINUX_GENERATION_COMPOSITION_IDENTITY_FIELDS",
    "LinuxGenerationCompositionOutcomeV1_2",
    "run_linux_generation_composition_v1_2_1",
)
