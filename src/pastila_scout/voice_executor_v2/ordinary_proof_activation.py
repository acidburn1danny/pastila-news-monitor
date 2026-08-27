"""Identity and isolation checks for ordinary-story proof-only authority."""

from __future__ import annotations

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

from .models import (
    OrdinaryStoryProofAuthorityAmendmentV1,
    OrdinaryStoryProofExpressionActivationAuthorityV1,
    VoiceOrdinaryStoryProofOnlyAuthorityV1,
)


def finalize_ordinary_story_proof_authority_v1(
    authority: VoiceOrdinaryStoryProofOnlyAuthorityV1,
) -> VoiceOrdinaryStoryProofOnlyAuthorityV1:
    payload = authority.model_dump(mode="json", exclude={"authority_identity"})
    return authority.model_copy(
        update={"authority_identity": canonical_identity(payload)}
    )


def verify_ordinary_story_proof_authority_v1(
    authority: VoiceOrdinaryStoryProofOnlyAuthorityV1,
) -> VoiceOrdinaryStoryProofOnlyAuthorityV1:
    expected = finalize_ordinary_story_proof_authority_v1(authority)
    if authority.authority_identity != expected.authority_identity:
        raise ValueError("ordinary-story proof authority identity mismatch")
    return authority


def reject_as_production_authority(authority: object) -> None:
    if isinstance(
        authority,
        (
            VoiceOrdinaryStoryProofOnlyAuthorityV1,
            OrdinaryStoryProofAuthorityAmendmentV1,
            OrdinaryStoryProofExpressionActivationAuthorityV1,
        ),
    ):
        raise TypeError(
            "ordinary-story proof-only authority is not production authority"
        )


def finalize_ordinary_story_proof_amendment_v1(
    amendment: OrdinaryStoryProofAuthorityAmendmentV1,
) -> OrdinaryStoryProofAuthorityAmendmentV1:
    payload = amendment.model_dump(mode="json", exclude={"amendment_identity"})
    return amendment.model_copy(
        update={"amendment_identity": canonical_identity(payload)}
    )


__all__ = [
    "finalize_ordinary_story_proof_amendment_v1",
    "finalize_ordinary_story_proof_authority_v1",
    "reject_as_production_authority",
    "verify_ordinary_story_proof_authority_v1",
]
