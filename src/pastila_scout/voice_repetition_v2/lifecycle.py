"""Explicit removal and publication transitions for committed Voice uses."""

from __future__ import annotations

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
)
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)
from pastila_scout.voice_workflow_v2 import semantic_draft_revision_identity

from .acceptance import (
    VoiceAcceptanceIntegrityError,
    VoiceAtomicAcceptanceStoreV1,
    _seal,
)
from .ledger import effective_uses_v1, finalize_ledger_v1
from .models import (
    PublicationStateV1,
    RepetitionLedgerEventKindV1,
    RepetitionLedgerEventV1,
    VoicePublicationReceiptV1,
    VoiceRemovalReceiptV1,
    VoiceRepetitionLedgerV1,
)
from .persistence import atomic_write


def remove_unpublished_commentary_v1(
    store: VoiceAtomicAcceptanceStoreV1,
    *,
    commit_identity: str,
    owner_identity: str,
    reason: str,
    removed_at,
) -> VoiceRemovalReceiptV1:
    ledger, draft = store.current_ledger(), store.current_draft()
    if draft is None:
        raise VoiceAcceptanceIntegrityError("no accepted draft to remove")
    effective = {item.commit_identity: item for item in effective_uses_v1(ledger)}
    use = effective.get(commit_identity)
    if use is None or use.publication_state is PublicationStateV1.PUBLISHED:
        raise VoiceAcceptanceIntegrityError("removal target is unavailable")
    transaction = canonical_identity(
        {
            "remove": commit_identity,
            "owner": owner_identity,
            "at": removed_at.isoformat(),
        }
    )
    directory = store.transactions / transaction.removeprefix("sha256:")
    stories = list(draft.stories)
    indexes = [
        index for index, story in enumerate(stories) if story.event_id == use.event_id
    ]
    if len(indexes) != 1 or stories[indexes[0]].acid_commentary is None:
        raise VoiceAcceptanceIntegrityError("accepted commentary is missing")
    stories[indexes[0]] = stories[indexes[0]].model_copy(
        update={
            "acid_commentary": None,
            "acid_commentary_status": "absent_owner_removed",
        }
    )
    authored = PastilaEditorSemanticDraftV2.assemble(
        episode_id=draft.episode_id,
        mode=SemanticDraftModeV2.CORE_PLUS_VOICE,
        stories=tuple(stories),
        transitions=draft.transitions,
        intro=draft.intro,
        final_monologue=draft.final_monologue,
        provenance_references=draft.provenance_references,
        generation_receipts=draft.generation_receipts,
    )
    event = RepetitionLedgerEventV1(
        sequence=len(ledger.events) + 1,
        event_kind=RepetitionLedgerEventKindV1.REVOKE,
        transaction_identity=transaction,
        target_commit_identity=commit_identity,
        actor_identity=owner_identity,
        reason=reason,
        occurred_at=removed_at,
    )
    next_ledger = finalize_ledger_v1(
        VoiceRepetitionLedgerV1(
            prior_ledger_identity=ledger.ledger_identity,
            events=ledger.events + (event,),
        )
    )
    draft_path, ledger_path, receipt_path = (
        directory / "accepted-draft.json",
        directory / "ledger.json",
        directory / "receipt.json",
    )
    atomic_write(draft_path, canonical_bytes(authored))
    atomic_write(ledger_path, canonical_bytes(next_ledger))
    provisional = VoiceRemovalReceiptV1(
        transaction_identity=transaction,
        removed_commit_identity=commit_identity,
        source_semantic_draft_revision_identity=semantic_draft_revision_identity(draft),
        resulting_semantic_draft_revision_identity=semantic_draft_revision_identity(
            authored
        ),
        committed_repetition_identity=next_ledger.ledger_identity,
        owner_identity=owner_identity,
        reason=reason,
        removed_at=removed_at,
    )
    receipt = provisional.model_copy(
        update={"receipt_identity": _seal(provisional, "receipt_identity")}
    )
    atomic_write(receipt_path, canonical_bytes(receipt))
    store._publish_state(
        transaction_identity=transaction,
        ledger_path=ledger_path,
        receipt_path=receipt_path,
        draft_path=draft_path,
    )
    return receipt


def publish_episode_uses_v1(
    store: VoiceAtomicAcceptanceStoreV1,
    *,
    publication_authority_identity: str,
    publisher_identity: str,
    published_at,
) -> VoicePublicationReceiptV1:
    ledger, draft = store.current_ledger(), store.current_draft()
    if draft is None:
        raise VoiceAcceptanceIntegrityError("no accepted draft to publish")
    targets = tuple(
        item.commit_identity
        for item in effective_uses_v1(ledger)
        if item.episode_id == draft.episode_id
        and item.publication_state is PublicationStateV1.UNPUBLISHED
    )
    if not targets:
        raise VoiceAcceptanceIntegrityError("no unpublished Voice use")
    transaction = canonical_identity(
        {
            "publish": targets,
            "authority": publication_authority_identity,
            "at": published_at.isoformat(),
        }
    )
    directory = store.transactions / transaction.removeprefix("sha256:")
    events = list(ledger.events)
    for target in targets:
        events.append(
            RepetitionLedgerEventV1(
                sequence=len(events) + 1,
                event_kind=RepetitionLedgerEventKindV1.PUBLISH,
                transaction_identity=transaction,
                target_commit_identity=target,
                actor_identity=publisher_identity,
                reason=f"publication:{publication_authority_identity}",
                occurred_at=published_at,
            )
        )
    next_ledger = finalize_ledger_v1(
        VoiceRepetitionLedgerV1(
            prior_ledger_identity=ledger.ledger_identity, events=tuple(events)
        )
    )
    draft_path, ledger_path, receipt_path = (
        directory / "accepted-draft.json",
        directory / "ledger.json",
        directory / "receipt.json",
    )
    atomic_write(draft_path, canonical_bytes(draft))
    atomic_write(ledger_path, canonical_bytes(next_ledger))
    provisional = VoicePublicationReceiptV1(
        transaction_identity=transaction,
        published_commit_identities=targets,
        publication_authority_identity=publication_authority_identity,
        resulting_semantic_draft_revision_identity=semantic_draft_revision_identity(
            draft
        ),
        committed_repetition_identity=next_ledger.ledger_identity,
        publisher_identity=publisher_identity,
        published_at=published_at,
    )
    receipt = provisional.model_copy(
        update={"receipt_identity": _seal(provisional, "receipt_identity")}
    )
    atomic_write(receipt_path, canonical_bytes(receipt))
    store._publish_state(
        transaction_identity=transaction,
        ledger_path=ledger_path,
        receipt_path=receipt_path,
        draft_path=draft_path,
    )
    return receipt


__all__ = ["publish_episode_uses_v1", "remove_unpublished_commentary_v1"]
