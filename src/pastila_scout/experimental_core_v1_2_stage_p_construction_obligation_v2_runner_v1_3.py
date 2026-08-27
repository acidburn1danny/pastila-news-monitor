"""Static V1.3 callback preflight over a bound V1.2 projector; never executes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import (
    ConstructionObligationV2RunnerProjectorPreflightV1_2,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_1 import (
    ConstructionObligationV2RequestBoundCallbackAdapterV1_1,
    request_bound_adapter_instance_identity_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    validate_no_legal_token_receipt_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_zero_model_callback_adapter_v1 import (
    ZeroModelCallbackDecisionV1,
)


RUNNER_CALLBACK_PREFLIGHT_IDENTITY = "f21bc27ccdbd1941783e2cfc893eede389e5a56207342a97d7fafc66b4506f91"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2RunnerCallbackPreflightV1_3:
    projector_preflight: ConstructionObligationV2RunnerProjectorPreflightV1_2
    callback: ConstructionObligationV2RequestBoundCallbackAdapterV1_1
    callback_instance_identity: str

    def project_input_ids(
        self, *, input_token_ids: Sequence[int], prompt_token_count: int,
        decode_generated: Callable[[Sequence[int]], str],
    ) -> ZeroModelCallbackDecisionV1:
        if type(prompt_token_count) is not int or prompt_token_count < 0:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_PROMPT_TOKEN_COUNT_INVALID")
        if isinstance(input_token_ids, (str, bytes)):
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_INPUT_TOKEN_IDS_INVALID")
        ids = tuple(input_token_ids)
        if any(type(item) is not int or item < 0 for item in ids):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_INPUT_TOKEN_IDS_INVALID")
        if len(ids) < prompt_token_count:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_INPUT_SHORTER_THAN_PROMPT")
        decision = self.callback.project(
            generated_token_ids=ids[prompt_token_count:], decode=decode_generated)
        if decision.no_legal_token_receipt is not None:
            validate_no_legal_token_receipt_v1(
                raw_receipt=decision.no_legal_token_receipt,
                request=self.projector_preflight.preflight.request)
        return decision


def bind_static_callback_preflight_v1_3(
    *, projector_preflight: ConstructionObligationV2RunnerProjectorPreflightV1_2,
) -> ConstructionObligationV2RunnerCallbackPreflightV1_3:
    if type(projector_preflight) is not ConstructionObligationV2RunnerProjectorPreflightV1_2:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_PROJECTOR_PREFLIGHT_V1_2_REQUIRED")
    base = projector_preflight.preflight
    callback = ConstructionObligationV2RequestBoundCallbackAdapterV1_1(
        request=base.request,
        source_binding=projector_preflight.static_payload.source_binding,
        token_pieces=base.token_piece_bundle.token_pieces,
    )
    instance_identity = request_bound_adapter_instance_identity_v1(callback)
    if (callback.request.source_context_identity !=
            projector_preflight.projector.request_context_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_PROJECTOR_CONTEXT_MISMATCH")
    return ConstructionObligationV2RunnerCallbackPreflightV1_3(
        projector_preflight, callback, instance_identity)


__all__ = (
    "ConstructionObligationV2RunnerCallbackPreflightV1_3",
    "RUNNER_CALLBACK_PREFLIGHT_IDENTITY", "bind_static_callback_preflight_v1_3",
)
