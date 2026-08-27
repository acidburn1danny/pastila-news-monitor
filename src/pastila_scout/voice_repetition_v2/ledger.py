"""Canonical ledger sealing, effective history, and snapshot derivation."""

from __future__ import annotations

from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2.engine import finalize_repetition_snapshot
from pastila_scout.voice_eligibility_v2.models import (
    RepetitionUseV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

from .models import (
    ZERO,
    CommittedVoiceUseV1,
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
    RepetitionLedgerEventKindV1,
    RepetitionSnapshotEnvelopeV1,
    VoiceRepetitionLedgerV1,
)


class VoiceRepetitionIntegrityError(ValueError):
    pass


def _seal(value, field: str) -> str:
    return canonical_identity(value.model_copy(update={field: ZERO}))


def finalize_order_authority_v1(
    value: EpisodeOrderAuthorityV1,
) -> EpisodeOrderAuthorityV1:
    return value.model_copy(
        update={"authority_identity": _seal(value, "authority_identity")}
    )


def finalize_ledger_v1(value: VoiceRepetitionLedgerV1) -> VoiceRepetitionLedgerV1:
    events = tuple(
        item.model_copy(update={"event_identity": _seal(item, "event_identity")})
        for item in value.events
    )
    provisional = value.model_copy(update={"events": events, "ledger_identity": ZERO})
    return provisional.model_copy(
        update={"ledger_identity": _seal(provisional, "ledger_identity")}
    )


def validate_ledger_v1(value: VoiceRepetitionLedgerV1) -> None:
    if finalize_ledger_v1(value) != value:
        raise VoiceRepetitionIntegrityError("ledger identity mismatch")


def effective_uses_v1(
    ledger: VoiceRepetitionLedgerV1,
) -> tuple[CommittedVoiceUseV1, ...]:
    validate_ledger_v1(ledger)
    commits: dict[str, CommittedVoiceUseV1] = {}
    revoked: set[str] = set()
    published: set[str] = set()
    for item in ledger.events:
        if item.event_kind is RepetitionLedgerEventKindV1.COMMIT:
            assert item.commit is not None
            commits[item.commit.commit_identity] = item.commit
        elif item.event_kind is RepetitionLedgerEventKindV1.REVOKE:
            assert item.target_commit_identity is not None
            revoked.add(item.target_commit_identity)
        else:
            assert item.target_commit_identity is not None
            published.add(item.target_commit_identity)
    return tuple(
        use.model_copy(update={"publication_state": PublicationStateV1.PUBLISHED})
        if identity in published
        else use
        for identity, use in commits.items()
        if identity not in revoked
    )


def derive_repetition_snapshot_v1(
    *,
    ledger: VoiceRepetitionLedgerV1,
    order_authority: EpisodeOrderAuthorityV1,
    event_id: int,
) -> RepetitionSnapshotEnvelopeV1:
    validate_ledger_v1(ledger)
    if finalize_order_authority_v1(order_authority) != order_authority:
        raise VoiceRepetitionIntegrityError("order authority identity mismatch")
    try:
        position = order_authority.ordered_event_ids.index(event_id) + 1
    except ValueError as exc:
        raise VoiceRepetitionIntegrityError(
            "story absent from governed episode order"
        ) from exc
    relevant = tuple(
        use
        for use in effective_uses_v1(ledger)
        if (
            use.episode_id == order_authority.episode_id
            and use.story_position < position
        )
        or (
            use.episode_ordinal < order_authority.episode_ordinal
            and use.publication_state is PublicationStateV1.PUBLISHED
        )
    )
    uses = tuple(
        RepetitionUseV1(
            episode_ordinal=item.episode_ordinal,
            story_position=item.story_position,
            mechanic_id=MechanicIdV1(item.mechanic_identity),
            program_id=item.realization_program_identity,
            cadence_signature=item.cadence_signature,
            surface_ids=item.approved_voice_surface_identities
            + (
                (item.expression_surface_identity,)
                if item.expression_surface_identity
                else ()
            ),
            enrichment_identity=item.expression_identity,
        )
        for item in relevant
    )
    snapshot = finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=order_authority.episode_ordinal,
            current_story_position=position,
            uses=uses,
            snapshot_identity=ZERO,
        )
    )
    provisional = RepetitionSnapshotEnvelopeV1(
        ledger_identity=ledger.ledger_identity,
        order_authority_identity=order_authority.authority_identity,
        snapshot=snapshot,
        exact_surface_identities=tuple(
            sorted(
                {
                    surface
                    for item in relevant
                    for surface in item.approved_voice_surface_identities
                    + (
                        (item.expression_surface_identity,)
                        if item.expression_surface_identity
                        else ()
                    )
                }
            )
        ),
        expression_family_identities=tuple(
            sorted(
                {
                    item.expression_family_identity
                    for item in relevant
                    if item.expression_family_identity
                }
            )
        ),
        expression_pool_identities=tuple(
            sorted(
                {
                    item.expression_pool_identity
                    for item in relevant
                    if item.expression_pool_identity
                }
            )
        ),
        callback_identities=tuple(
            sorted({value for item in relevant for value in item.callback_identities})
        ),
        mapping_identities=tuple(
            sorted({value for item in relevant for value in item.mapping_identities})
        ),
    )
    return provisional.model_copy(
        update={"envelope_identity": _seal(provisional, "envelope_identity")}
    )


__all__ = [
    "VoiceRepetitionIntegrityError",
    "derive_repetition_snapshot_v1",
    "effective_uses_v1",
    "finalize_ledger_v1",
    "finalize_order_authority_v1",
    "validate_ledger_v1",
]
