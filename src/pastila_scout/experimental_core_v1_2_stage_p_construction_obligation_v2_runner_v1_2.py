"""Static V1.2 request/token-piece/projector preflight; never executes."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import (
    ConstructionObligationV2RunnerPreflightV1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import (
    ConstructionObligationV2HostWslPayloadV1,
    parse_construction_obligation_v2_host_wsl_payload_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    ConstructionObligationV2StaticPayloadV1,
    parse_construction_obligation_v2_static_payload_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v1 import (
    StagePConstructionObligationV2TokenProjectorV1,
)


RUNNER_PROJECTOR_PREFLIGHT_IDENTITY = "83074527007e585be686caac6a6951df000e3de0052ff104e45bdc529ce44908"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2RunnerProjectorPreflightV1_2:
    preflight: ConstructionObligationV2RunnerPreflightV1_1
    host_payload: ConstructionObligationV2HostWslPayloadV1
    static_payload: ConstructionObligationV2StaticPayloadV1
    projector: StagePConstructionObligationV2TokenProjectorV1


def bind_static_projector_preflight_v1_2(
    *, preflight: ConstructionObligationV2RunnerPreflightV1_1,
) -> ConstructionObligationV2RunnerProjectorPreflightV1_2:
    if type(preflight) is not ConstructionObligationV2RunnerPreflightV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_PREFLIGHT_V1_1_REQUIRED")
    request = preflight.request
    host = parse_construction_obligation_v2_host_wsl_payload_v1(
        raw_payload=request.host_payload)
    if (hashlib.sha256(request.host_payload).hexdigest() != request.host_payload_sha256 or
            host.provider_request_id != request.provider_request_id or
            host.source_context_identity != request.source_context_identity or
            host.max_output_tokens != request.max_output_tokens):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_HOST_BINDING_MISMATCH")
    static = parse_construction_obligation_v2_static_payload_v1(
        raw_payload=host.static_payload)
    if (static.payload_sha256 != host.static_payload_sha256 or
            static.source_binding.source_context_identity != request.source_context_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_STATIC_BINDING_MISMATCH")
    projector = static.bind_projector(
        token_pieces=preflight.token_piece_bundle.token_pieces)
    bundle = preflight.token_piece_bundle
    if (projector.tokenizer_identity != bundle.tokenizer_identity or
            projector.decoder_identity != bundle.decoder_identity or
            projector.eos_token_id != bundle.eos_token_id or
            projector.request_context_identity != request.source_context_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_PROJECTOR_BINDING_MISMATCH")
    return ConstructionObligationV2RunnerProjectorPreflightV1_2(
        preflight, host, static, projector)


__all__ = (
    "ConstructionObligationV2RunnerProjectorPreflightV1_2",
    "RUNNER_PROJECTOR_PREFLIGHT_IDENTITY", "bind_static_projector_preflight_v1_2",
)
