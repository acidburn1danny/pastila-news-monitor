"""Static provider-execution-request binding for Construction-Obligation V2."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pastila_scout.application_request_authority_v1 import (
    ApplicationRequestAuthorityV1,
)
from pastila_scout.provider_execution_v2 import ProviderExecutionRequestV2

from .stage_p_construction_obligation_v2_application_request_v1 import (
    MODEL_IDENTITY,
    POLICY_IDENTITY,
    PROMPT_RENDERER_IDENTITY,
    ConstructionObligationV2ApplicationRequestCandidateV1,
)
from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    PROJECTOR_FREEZE_IDENTITY,
)


APPLICATION_REQUEST_CANDIDATE_IDENTITY = (
    "b245de18f8864edb4be73ee12c04eb3c47f0a05cc3a3859bc49dd7fbd9cecd89"
)
APPLICATION_REQUEST_AUTHORITY_SHA256 = (
    "61523b3dc1e0a5af9b17863efb8163746235f6ba4f3fdea0c32dea4e0eb696e4"
)
PROVIDER_EXECUTION_MODELS_SHA256 = (
    "011192c8b5bc78303098200c59cb679c53bcca74d08dcda0859cc46453cc8ba2"
)
OLLAMA_DESCRIPTOR_IDENTITY = (
    "scout:provider-descriptor-v2:"
    "72aec3ff060fbedee82a8264c15e2033f07bd99ea84cdb0152c637cf4aa0f159"
)
OLLAMA_DESCRIPTOR_FINGERPRINT = (
    "137f2e1dc7b5840c31a88b1ff664ff6e915c8f233d6b9e1dc4c7e221cdf8a507"
)
OLLAMA_ADAPTER_IDENTITY = (
    "scout:provider-adapter-v2:"
    "de70e253f535e82f8443680cc8e0a0dc041c50d918ec4a81df1445aa8bb73ce9"
)
BINDING_IDENTITY = "02ab80de6c994bede334dc87faaa20a30302d445a8ac162494428789df1b6cc5"


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2ProviderExecutionRequestBindingV1:
    binding_identity: str
    projector_freeze_identity: str
    application_request_candidate_identity: str
    application_request_identity: str
    provider_descriptor_identity: str
    provider_descriptor_fingerprint: str
    provider_adapter_identity: str
    provider_execution_request: ProviderExecutionRequestV2


def bind_construction_obligation_v2_provider_execution_request_v1(
    *, candidate: ConstructionObligationV2ApplicationRequestCandidateV1,
) -> ConstructionObligationV2ProviderExecutionRequestBindingV1:
    """Construct provider-bound request authority without invoking execution."""
    _verify_candidate(candidate)
    request = ApplicationRequestAuthorityV1().build(candidate.application_request)
    provider = request.provider
    observed = (
        provider.identity,
        provider.fingerprint,
        provider.adapter_identity,
        provider.provider_id,
        tuple(str(item) for item in provider.capabilities),
    )
    expected = (
        OLLAMA_DESCRIPTOR_IDENTITY,
        OLLAMA_DESCRIPTOR_FINGERPRINT,
        OLLAMA_ADAPTER_IDENTITY,
        "ollama",
        ("metadata",),
    )
    if observed != expected:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PROVIDER_DESCRIPTOR_MISMATCH")
    rebuilt = ProviderExecutionRequestV2.model_validate(
        request.model_dump(mode="python", warnings=False), strict=True
    )
    if rebuilt != request:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EXECUTION_REQUEST_REBUILD_MISMATCH")
    return ConstructionObligationV2ProviderExecutionRequestBindingV1(
        BINDING_IDENTITY,
        PROJECTOR_FREEZE_IDENTITY,
        APPLICATION_REQUEST_CANDIDATE_IDENTITY,
        candidate.application_request_identity,
        provider.identity,
        provider.fingerprint,
        provider.adapter_identity,
        rebuilt,
    )


def _verify_candidate(
    candidate: ConstructionObligationV2ApplicationRequestCandidateV1,
) -> None:
    if type(candidate) is not ConstructionObligationV2ApplicationRequestCandidateV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_APPLICATION_CANDIDATE_EXACT_TYPE_REQUIRED")
    request = candidate.application_request
    fields = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_APPLICATION_REQUEST_V1",
        POLICY_IDENTITY,
        PROMPT_RENDERER_IDENTITY,
        MODEL_IDENTITY,
        candidate.rendered_request_identity,
        request.provider.value,
        str(request.timeout_policy.timeout_seconds),
        "CANCELLATION_FALSE",
        request.requested_at.isoformat(),
        request.request_reference,
    )
    expected_identity = hashlib.sha256("\n".join(fields).encode()).hexdigest()
    if (
        candidate.policy_identity != POLICY_IDENTITY
        or candidate.prompt_renderer_identity != PROMPT_RENDERER_IDENTITY
        or candidate.model_identity != MODEL_IDENTITY
        or candidate.application_request_identity != expected_identity
        or request.provider.value != "ollama"
        or request.timeout_policy.timeout_seconds != 240.0
        or request.cancellation.cancellation_requested is not False
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_APPLICATION_CANDIDATE_IDENTITY_MISMATCH")


__all__ = (
    "BINDING_IDENTITY",
    "ConstructionObligationV2ProviderExecutionRequestBindingV1",
    "bind_construction_obligation_v2_provider_execution_request_v1",
)
