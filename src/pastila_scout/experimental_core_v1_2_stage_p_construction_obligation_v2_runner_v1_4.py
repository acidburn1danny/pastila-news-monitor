"""Zero-execution V1.4 lifecycle preamble; stops before model loading."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import (
    ConstructionObligationV2RunnerCallbackPreflightV1_3,
    RUNNER_CALLBACK_PREFLIGHT_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    build_lifecycle_event_v1,
)


RUNNER_LIFECYCLE_PREAMBLE_IDENTITY = "a4f958ac8b793da4e5c9d2d91145b8d49c2ca8624d209e9aed0670eced35f678"
_EVENTS = (
    "REQUEST_VALIDATED", "TOKENIZER_IDENTITY_VALIDATED", "PROJECTOR_CONSTRUCTED")


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2RunnerLifecyclePreambleV1_4:
    callback_preflight: ConstructionObligationV2RunnerCallbackPreflightV1_3
    events: tuple[bytes, bytes, bytes]
    terminal_event_identity: str


def build_zero_execution_lifecycle_preamble_v1_4(
    *, callback_preflight: ConstructionObligationV2RunnerCallbackPreflightV1_3,
) -> ConstructionObligationV2RunnerLifecyclePreambleV1_4:
    if type(callback_preflight) is not ConstructionObligationV2RunnerCallbackPreflightV1_3:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_CALLBACK_PREFLIGHT_V1_3_REQUIRED")
    projector_preflight = callback_preflight.projector_preflight
    base = projector_preflight.preflight
    request = base.request
    if (callback_preflight.callback_instance_identity == "" or
            projector_preflight.projector.request_context_identity != request.source_context_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_LIFECYCLE_PREAMBLE_BINDING_MISMATCH")
    pieces_digest = hashlib.sha256()
    for token_id, piece in sorted(base.token_piece_bundle.token_pieces.items()):
        pieces_digest.update(str(token_id).encode("ascii"))
        pieces_digest.update(b"\0")
        pieces_digest.update(piece.encode("utf-8"))
        pieces_digest.update(b"\n")
    details = (
        {
            "runner_callback_preflight_identity": RUNNER_CALLBACK_PREFLIGHT_IDENTITY,
            "host_payload_sha256": request.host_payload_sha256,
            "source_context_identity": request.source_context_identity,
        },
        {
            "tokenizer_identity": base.token_piece_bundle.tokenizer_identity,
            "decoder_identity": base.token_piece_bundle.decoder_identity,
            "token_piece_sha256": pieces_digest.hexdigest(),
            "excluded_token_count": len(base.token_piece_bundle.excluded_token_ids),
        },
        {
            "projector_freeze_identity": base.token_piece_bundle.projector_freeze_identity,
            "request_context_identity": projector_preflight.projector.request_context_identity,
            "callback_instance_identity": callback_preflight.callback_instance_identity,
        },
    )
    raw_events = []
    previous = None
    for sequence, (event, detail) in enumerate(zip(_EVENTS, details, strict=True)):
        raw = build_lifecycle_event_v1(
            request=request, sequence=sequence, event=event, detail=detail,
            previous_event_identity=previous)
        value = json.loads(raw)
        if value["event"] != event or value["sequence"] != sequence:
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_LIFECYCLE_PREAMBLE_EVENT_MISMATCH")
        previous = value["event_identity"]
        raw_events.append(raw)
    return ConstructionObligationV2RunnerLifecyclePreambleV1_4(
        callback_preflight, tuple(raw_events), previous)


__all__ = (
    "ConstructionObligationV2RunnerLifecyclePreambleV1_4",
    "RUNNER_LIFECYCLE_PREAMBLE_IDENTITY",
    "build_zero_execution_lifecycle_preamble_v1_4",
)
