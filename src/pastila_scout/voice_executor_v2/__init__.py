"""Public deterministic Voice V2 production-binding foundation."""

from .executor import (
    RENDERER_IDENTITY,
    ZERO_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
    ProofOnlyDeterministicVoiceExecutorV2,
    VoiceExecutorPortV2,
    build_governed_execution_request_v2,
    finalize_activation_policy_v1,
    finalize_request_v2,
)
from .models import *
from .ordinary_proof_activation import (
    finalize_ordinary_story_proof_amendment_v1,
    finalize_ordinary_story_proof_authority_v1,
    reject_as_production_authority,
    verify_ordinary_story_proof_authority_v1,
)
from .persistence import (
    DeterministicVoiceSidecarIntegrityError,
    UnknownDeterministicVoiceSidecarVersionError,
    VoiceDeterministicPreviewSidecarStoreV2,
    build_preview_sidecar_v2,
    finalize_preview_sidecar_v2,
)
_PROOF_ACTIVATION_EXPORTS = {
    "FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1",
    "finalize_proof_activation_authority_v1",
}
_PROOF_EXPRESSION_ACTIVATION_EXPORTS = {
    "finalize_proof_expression_authority_v1",
    "materialize_proof_only_ordinary_story_ir_v1_1",
    "reject_proof_expression_authority_as_production",
    "verify_and_render_proof_only_ordinary_story_ir_v1_1",
    "verify_proof_expression_authority_v1",
}


def __getattr__(name: str):
    if name == "BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1":
        from .production_activation import (
            BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1,
        )

        return BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1
    if name in _PROOF_ACTIVATION_EXPORTS:
        from . import proof_activation

        return getattr(proof_activation, name)
    if name in _PROOF_EXPRESSION_ACTIVATION_EXPORTS:
        from . import proof_expression_activation

        return getattr(proof_expression_activation, name)
    raise AttributeError(name)


__all__ = [
    "BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1",
    "FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1",
    "RENDERER_IDENTITY",
    "ZERO_ACTIVATION_POLICY_V1",
    "DeterministicVoiceExecutorV2",
    "DeterministicVoiceSidecarIntegrityError",
    "ProofOnlyDeterministicVoiceExecutorV2",
    "UnknownDeterministicVoiceSidecarVersionError",
    "VoiceDeterministicPreviewSidecarStoreV2",
    "VoiceExecutorPortV2",
    "build_governed_execution_request_v2",
    "build_preview_sidecar_v2",
    "finalize_activation_policy_v1",
    "finalize_ordinary_story_proof_amendment_v1",
    "finalize_ordinary_story_proof_authority_v1",
    "finalize_preview_sidecar_v2",
    "finalize_proof_activation_authority_v1",
    "finalize_proof_expression_authority_v1",
    "finalize_request_v2",
    "materialize_proof_only_ordinary_story_ir_v1_1",
    "reject_as_production_authority",
    "reject_proof_expression_authority_as_production",
    "verify_and_render_proof_only_ordinary_story_ir_v1_1",
    "verify_ordinary_story_proof_authority_v1",
    "verify_proof_expression_authority_v1",
]
