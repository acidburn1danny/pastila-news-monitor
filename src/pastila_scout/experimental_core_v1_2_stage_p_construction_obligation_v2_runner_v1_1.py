"""Static V1.1 runner preflight binding; no loader or execution surface."""
from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    RunnerRequestV1,
    parse_runner_request_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    InjectedTokenizerV1,
    TokenizerRuntimeIdentityV1,
    TokenPieceBundleV1,
)

RUNNER_PREFLIGHT_IDENTITY = "7a8ad4379362debbbf72425d3c2328bc9bed778b45fe083a42d47f8407428b52"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2RunnerPreflightV1_1:
    request: RunnerRequestV1
    token_piece_bundle: TokenPieceBundleV1


def validate_request_only_v1_1(*, raw_request: bytes) -> RunnerRequestV1:
    if type(raw_request) is not bytes or not raw_request or len(raw_request) > 600_000:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_BYTES_REQUIRED")
    return parse_runner_request_v1(raw_request=raw_request)


def bind_injected_tokenizer_preflight_v1_1(
    *, validated_request: RunnerRequestV1, tokenizer: InjectedTokenizerV1,
    tokenizer_runtime_identity: TokenizerRuntimeIdentityV1,
) -> ConstructionObligationV2RunnerPreflightV1_1:
    if type(validated_request) is not RunnerRequestV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_VALIDATED_RUNNER_REQUEST_REQUIRED")
    if (not validated_request.provider_request_id or
            not validated_request.source_context_identity or
            len(validated_request.host_payload_sha256) != 64):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_BINDING_INVALID")
    del tokenizer, tokenizer_runtime_identity
    raise RuntimeError(
        "CONSTRUCTION_OBLIGATION_V2_RUNNER_V1_1_SUPERSEDED_BY_PROVENANCE_BOUND_RUNTIME"
    )


__all__ = (
    "RUNNER_PREFLIGHT_IDENTITY",
    "ConstructionObligationV2RunnerPreflightV1_1",
    "bind_injected_tokenizer_preflight_v1_1",
    "validate_request_only_v1_1",
)
