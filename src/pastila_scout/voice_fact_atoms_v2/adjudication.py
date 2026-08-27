"""Explicit owner/editor adjudication; no approval is inferred."""

from __future__ import annotations

from .models import (
    AdjudicationAction,
    AdjudicationReceiptV1,
    FactAtomV1,
    VoiceFactAtomBundleV1,
)
from .persistence import bundle_payload_identity, canonical_identity


def apply_adjudication(
    *,
    prior: VoiceFactAtomBundleV1,
    receipt: AdjudicationReceiptV1,
    resulting_atoms: tuple[FactAtomV1, ...],
) -> VoiceFactAtomBundleV1:
    if receipt.receipt_identity != canonical_identity(
        receipt.model_copy(update={"receipt_identity": "sha256:" + "0" * 64})
    ):
        raise ValueError("adjudication receipt identity mismatch")
    known = {item.candidate_id for item in prior.candidates}
    produced = {item.atom_id for item in resulting_atoms}
    for decision in receipt.decisions:
        if not set(decision.candidate_ids) <= known:
            raise ValueError("adjudication references unknown candidate")
        if (
            decision.action is not AdjudicationAction.REJECT
            and not set(decision.resulting_atom_ids) <= produced
        ):
            raise ValueError("adjudication result atom missing")
    payload = prior.model_dump(mode="python")
    payload.update(
        revision=prior.revision + 1,
        atoms=resulting_atoms,
        adjudication_receipt_identities=prior.adjudication_receipt_identities
        + (receipt.receipt_identity,),
        bundle_identity="sha256:" + "0" * 64,
    )
    provisional = VoiceFactAtomBundleV1.model_validate(payload)
    return provisional.model_copy(
        update={"bundle_identity": bundle_payload_identity(provisional)}
    )
