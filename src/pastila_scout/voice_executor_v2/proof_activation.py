"""Explicit non-production activation authority for frozen Voice proof cases."""

from __future__ import annotations

from pastila_scout.voice_deterministic_v2.library import FROZEN_PROOF_CASES_V1
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

from .models import (
    ZERO_IDENTITY,
    ProofActivationEntryV1,
    VoiceProofOnlyActivationAuthorityV1,
)


def finalize_proof_activation_authority_v1(
    authority: VoiceProofOnlyActivationAuthorityV1,
) -> VoiceProofOnlyActivationAuthorityV1:
    sealed = authority.model_copy(update={"authority_identity": ZERO_IDENTITY})
    return authority.model_copy(
        update={"authority_identity": canonical_identity(sealed)}
    )


FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1 = finalize_proof_activation_authority_v1(
    VoiceProofOnlyActivationAuthorityV1(
        entries=tuple(
            ProofActivationEntryV1(
                proof_id=case.proof_id,
                source_record_id=case.source_record_id,
                realization_program_id=case.realization_program_id,
                realization_program_sha256=case.realization_program_sha256,
                expected_output_sha256=case.expected_output_sha256,
                expected_abstention_reason=(
                    case.expected_abstention_reason.value
                    if case.expected_abstention_reason
                    else None
                ),
            )
            for case in FROZEN_PROOF_CASES_V1.values()
        )
    )
)


__all__ = [
    "FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1",
    "finalize_proof_activation_authority_v1",
]
