"""Source-only composition of the frozen Linux generation components.

Calling :func:`run_linux_generation_composition_v1` crosses the separately
authorized process/model/generation boundary.  Importing this module performs
no filesystem, process, WSL, tokenizer, model, or generation operation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    DurableArtifactReceiptV1,
    DurableEvidenceRootBindingV1,
    create_durable_filesystem_sink_v1,
)
from .stage_p_construction_obligation_v2_generation_authority_contract_v1 import (
    parse_generation_authority_v1,
)
from .stage_p_construction_obligation_v2_linux_child_process_adapter_v1 import (
    build_linux_child_process_operations_v1,
)
from .stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    SUPERVISOR_CANDIDATE_IDENTITY,
    InjectedDurableSinkV1,
    LinuxGenerationSupervisorOutcomeV1,
    supervise_linux_generation_candidate_v1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    parse_runner_request_v1,
)

LINUX_GENERATION_COMPOSITION_IDENTITY = (
    "c52b5126add3f7975e3e630a618db81549dc74aeea2ab0b6756b6e0d8582e183"
)


@dataclass(frozen=True, slots=True)
class LinuxGenerationCompositionOutcomeV1:
    composition_identity: str
    sink_instance_identity: str
    supervisor_outcome: LinuxGenerationSupervisorOutcomeV1
    durable_receipts: tuple[DurableArtifactReceiptV1, ...]


def run_linux_generation_composition_v1(
    *,
    raw_policy_receipt: bytes,
    raw_authority_receipt: bytes,
    raw_runner_request: bytes,
    system_prompt: str,
    evidence_root: Path,
    timeout_seconds: float,
    context_factory: Callable[[str], object] | None = None,
) -> LinuxGenerationCompositionOutcomeV1:
    """Validate, create one evidence root, then invoke one Linux supervisor."""
    request = parse_runner_request_v1(raw_request=raw_runner_request)
    authority = parse_generation_authority_v1(
        raw_receipt=raw_authority_receipt,
        expected_generation_candidate_identity=SUPERVISOR_CANDIDATE_IDENTITY,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    child_operations = build_linux_child_process_operations_v1(
        raw_policy_receipt=raw_policy_receipt,
        raw_authority_receipt=raw_authority_receipt,
        context_factory=context_factory,
    )
    sink = create_durable_filesystem_sink_v1(
        root=evidence_root,
        binding=DurableEvidenceRootBindingV1(
            request.provider_request_id,
            request.source_context_identity,
            authority.authority_receipt_identity,
            SUPERVISOR_CANDIDATE_IDENTITY,
        ),
    )
    durable_receipts: list[DurableArtifactReceiptV1] = []

    def persist(label: str, raw: bytes) -> None:
        receipt = sink.persist(label, raw)
        if type(receipt) is not DurableArtifactReceiptV1:
            raise TypeError(
                "CONSTRUCTION_OBLIGATION_V2_COMPOSITION_DURABLE_RECEIPT_EXACT_TYPE_REQUIRED"
            )
        if receipt.sink_instance_identity != sink.sink_instance_identity:
            raise ValueError(
                "CONSTRUCTION_OBLIGATION_V2_COMPOSITION_SINK_IDENTITY_MISMATCH"
            )
        durable_receipts.append(receipt)

    outcome = supervise_linux_generation_candidate_v1(
        raw_policy_receipt=raw_policy_receipt,
        raw_authority_receipt=raw_authority_receipt,
        raw_runner_request=raw_runner_request,
        system_prompt=system_prompt,
        timeout_seconds=timeout_seconds,
        child_operations=child_operations,
        durable_sink=InjectedDurableSinkV1(persist),
    )
    receipt_hashes = tuple(
        (receipt.label, receipt.sha256) for receipt in durable_receipts
    )
    if receipt_hashes != outcome.persisted_artifact_sha256:
        raise RuntimeError(
            "CONSTRUCTION_OBLIGATION_V2_COMPOSITION_DURABLE_RECONCILIATION_FAILED"
        )
    return LinuxGenerationCompositionOutcomeV1(
        LINUX_GENERATION_COMPOSITION_IDENTITY,
        sink.sink_instance_identity,
        outcome,
        tuple(durable_receipts),
    )


__all__ = (
    "LINUX_GENERATION_COMPOSITION_IDENTITY",
    "LinuxGenerationCompositionOutcomeV1",
    "run_linux_generation_composition_v1",
)
