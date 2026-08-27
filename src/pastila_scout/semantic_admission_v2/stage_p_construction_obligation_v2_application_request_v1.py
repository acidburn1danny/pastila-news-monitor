"""Pure ApplicationProviderRequestV1 construction for Construction-Obligation V2."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .stage_p_construction_obligation_v2_request_renderer_v1 import (
    DATA_BEGIN,
    DATA_END,
    DESIGN_IDENTITY,
    PROJECTOR_FREEZE_IDENTITY,
    PROMPT_SHA256,
    REQUEST_SCHEMA_NAME,
    REQUEST_SCHEMA_VERSION,
    STATIC_PAYLOAD_IDENTITY,
    V2_SCHEMA_IDENTITY,
    ConstructionObligationV2RenderedRequestV1,
)
from .stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    parse_construction_obligation_v2_static_payload_v1,
)


POLICY_IDENTITY = "42ea37912ec99d52c3ee0d7624f1daae442141a6ccf48f1fe527515851ea0c3f"
PROMPT_RENDERER_IDENTITY = "eb378b14eb6bc101b7cbf4af59759f3c428d0f8ae5115ee833ae59bf1c7e341d"
MODEL_IDENTITY = "pastila-editor-core-v1.2-experimental"
PROVIDER_CHOICE = ProviderChoiceV1.OLLAMA
TIMEOUT_SECONDS = 240.0


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2ApplicationRequestCandidateV1:
    policy_identity: str
    prompt_renderer_identity: str
    model_identity: str
    rendered_request_identity: str
    application_request_identity: str
    application_request: ApplicationProviderRequestV1


def build_construction_obligation_v2_application_request_v1(
    *, rendered_request: ConstructionObligationV2RenderedRequestV1,
    requested_at: datetime,
) -> ConstructionObligationV2ApplicationRequestCandidateV1:
    if type(rendered_request) is not ConstructionObligationV2RenderedRequestV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RENDERED_REQUEST_EXACT_TYPE_REQUIRED")
    if type(requested_at) is not datetime or requested_at.tzinfo is None or requested_at.utcoffset() is None:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_REQUESTED_AT_AWARE_REQUIRED")
    _verify_rendered_request(rendered_request)
    reference = (
        "semantic-admission-v2:stage-p-construction-obligation-v2:"
        + rendered_request.request_identity[:24])
    application = ApplicationProviderRequestV1(
        PROVIDER_CHOICE, rendered_request.rendered_prompt, reference, requested_at,
        TimeoutPolicyV2(timeout_seconds=TIMEOUT_SECONDS),
        CancellationTokenV2(cancellation_requested=False))
    identity_fields = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_APPLICATION_REQUEST_V1",
        POLICY_IDENTITY, PROMPT_RENDERER_IDENTITY, MODEL_IDENTITY,
        rendered_request.request_identity, PROVIDER_CHOICE.value,
        str(TIMEOUT_SECONDS), "CANCELLATION_FALSE", requested_at.isoformat(), reference)
    identity = hashlib.sha256("\n".join(identity_fields).encode()).hexdigest()
    return ConstructionObligationV2ApplicationRequestCandidateV1(
        POLICY_IDENTITY, PROMPT_RENDERER_IDENTITY, MODEL_IDENTITY,
        rendered_request.request_identity, identity, application)


def _verify_rendered_request(request: ConstructionObligationV2RenderedRequestV1) -> None:
    expected = (
        REQUEST_SCHEMA_NAME, REQUEST_SCHEMA_VERSION, DESIGN_IDENTITY,
        PROJECTOR_FREEZE_IDENTITY, STATIC_PAYLOAD_IDENTITY,
        V2_SCHEMA_IDENTITY, PROMPT_SHA256)
    observed = (
        request.schema_name, request.schema_version, request.design_identity,
        request.projector_freeze_identity, request.static_payload_identity,
        request.v2_schema_identity, request.prompt_sha256)
    if observed != expected:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_REQUEST_IDENTITY_MISMATCH")
    rendered = request.rendered_prompt.encode("utf-8")
    if (len(rendered) != request.rendered_prompt_utf8_bytes or
            hashlib.sha256(rendered).hexdigest() != request.rendered_prompt_sha256):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_PROMPT_BYTES_MISMATCH")
    begin = b"\n" + DATA_BEGIN + b"\n"
    end = DATA_END
    if rendered.count(begin) != 1 or rendered.count(end) != 1 or not rendered.endswith(end):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_PROMPT_DELIMITER_MISMATCH")
    payload = rendered.split(begin, 1)[1][:-len(end)]
    if hashlib.sha256(payload).hexdigest() != request.static_payload_sha256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_HASH_MISMATCH")
    parse_construction_obligation_v2_static_payload_v1(raw_payload=payload)
    identity_fields = (
        REQUEST_SCHEMA_NAME, REQUEST_SCHEMA_VERSION, DESIGN_IDENTITY,
        PROJECTOR_FREEZE_IDENTITY, STATIC_PAYLOAD_IDENTITY,
        V2_SCHEMA_IDENTITY, PROMPT_SHA256, request.static_payload_sha256,
        request.rendered_prompt_sha256)
    if hashlib.sha256("\n".join(identity_fields).encode()).hexdigest() != request.request_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_REQUEST_IDENTITY_MISMATCH")


__all__ = (
    "ConstructionObligationV2ApplicationRequestCandidateV1",
    "build_construction_obligation_v2_application_request_v1",
)
