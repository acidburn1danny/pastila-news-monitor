from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AuthorityDensityV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
)
from pastila_scout.voice_fact_atoms_v2 import (
    AdjudicationAction,
    AdjudicationDecisionV1,
    AdjudicationReceiptV1,
    AtomKind,
    AuthorityClass,
    CompleteQuantityV1,
    FactAtomBundleIntegrityError,
    FactAtomV1,
    UnknownFactAtomBundleVersionError,
    VoiceFactAtomBundleStoreV1,
    VoiceFactAtomBundleV1,
    apply_adjudication,
    canonical_identity,
    extract_surface_candidates,
    finalize_bundle_identity,
)
from pastila_scout.voice_workflow_v2 import (
    semantic_draft_revision_identity,
    sha256_identity,
)

ZERO = "sha256:" + "0" * 64


def _sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _draft(text: str = "Proiectul a costat aproximativ 37000 de euro."):
    summary = FactualSummaryV2(
        text=text,
        authority_bundle_identity=_sha("authority"),
        authority_density=AuthorityDensityV2.THIN,
        nucleus_bindings=(
            FactualNucleusBindingV2(
                nucleus_id="n1", sentence_number=1, authority_fact_ids=("f1",)
            ),
        ),
        model_identifier="core-v1.2",
        provider="ollama",
        validation_receipt="pass",
    )
    story = SemanticStoryV2(
        event_id=7,
        position=1,
        factual_summary=summary,
        acid_commentary=None,
        acid_commentary_status="absent_voice_layer_unavailable",
    )
    return PastilaEditorSemanticDraftV2.assemble(
        episode_id="ep", mode=SemanticDraftModeV2.CORE_ONLY, stories=(story,)
    )


def _bundle(draft, candidates=(), atoms=()):
    story = draft.stories[0]
    provisional = VoiceFactAtomBundleV1(
        revision=1,
        semantic_draft_revision_identity=semantic_draft_revision_identity(draft),
        event_id=7,
        story_position=1,
        factual_summary_identity=sha256_identity(story.factual_summary.text),
        event_authority_identity=story.factual_summary.authority_bundle_identity,
        candidates=candidates,
        atoms=atoms,
        bundle_identity=ZERO,
    )
    return finalize_bundle_identity(provisional)


@pytest.mark.parametrize(
    "surface",
    [
        "aproximativ 37.000 de euro",
        "133 de tranzacții",
        "ar fi primit bani",
        "motivul nu se știe",
        "rămâne o suspiciune",
        "decizia poate fi contestată",
    ],
)
def test_surface_extraction_is_exact_and_never_semantically_accepted(surface):
    candidates = extract_surface_candidates(
        authority_class=AuthorityClass.EVENT,
        authority_identity=_sha("authority"),
        source_identity="source:1",
        text=surface,
    )
    assert candidates
    assert all(item.requires_semantic_adjudication for item in candidates)
    assert all(
        item.evidence.passage == surface[item.evidence.start : item.evidence.end]
        for item in candidates
    )


def test_quantity_is_indivisible_and_approximation_cannot_be_lost():
    valid = CompleteQuantityV1(
        exact_surface="aproximativ 37.000 de euro",
        numeric_surface="37.000",
        approximation="aproximativ",
        bound_semantics="approximate",
        unit_or_currency="euro",
        subject_scope="coteț mobil",
    )
    assert valid.bound_semantics == "approximate"
    with pytest.raises(ValueError, match="approximation"):
        CompleteQuantityV1(
            exact_surface="37.000 de euro",
            numeric_surface="37.000",
            approximation="aproximativ",
            bound_semantics="approximate",
            unit_or_currency="euro",
            subject_scope="coteț",
        )


def test_epistemic_and_causal_atoms_require_exact_target():
    candidate = extract_surface_candidates(
        authority_class=AuthorityClass.EVENT,
        authority_identity=_sha("authority"),
        source_identity="s",
        text="ar fi primit bani",
    )[0]
    with pytest.raises(ValueError, match="exact target"):
        FactAtomV1(
            atom_id="a",
            kind=AtomKind.ALLEGATION_STATUS,
            proposition="este o acuzație",
            authority_class=AuthorityClass.EVENT,
            evidence=(candidate.evidence,),
            candidate_ids=(candidate.candidate_id,),
        )


def test_background_atom_cannot_project_into_event():
    candidate = extract_surface_candidates(
        authority_class=AuthorityClass.BACKGROUND,
        authority_identity=_sha("background"),
        source_identity="official",
        text="Cyber Command există",
    )[0]
    with pytest.raises(ValueError, match="prohibit event projection"):
        FactAtomV1(
            atom_id="bg",
            kind=AtomKind.BACKGROUND_PROPOSITION,
            proposition="Cyber Command există",
            authority_class=AuthorityClass.BACKGROUND,
            evidence=(candidate.evidence,),
            candidate_ids=(candidate.candidate_id,),
        )


def test_explicit_adjudication_creates_new_revision_and_receipt():
    draft = _draft()
    candidates = extract_surface_candidates(
        authority_class=AuthorityClass.EVENT,
        authority_identity=_sha("authority"),
        source_identity="s",
        text=draft.stories[0].factual_summary.text,
    )
    prior = _bundle(draft, candidates)
    quantity_candidate = next(
        item for item in candidates if item.kind.value == "complete_quantity"
    )
    quantity = CompleteQuantityV1(
        exact_surface=quantity_candidate.evidence.passage,
        numeric_surface="37000",
        approximation="aproximativ",
        bound_semantics="approximate",
        unit_or_currency="euro",
        subject_scope="proiect",
    )
    atom = FactAtomV1(
        atom_id="quantity-1",
        kind=AtomKind.COMPLETE_QUANTITY,
        proposition=quantity.exact_surface,
        authority_class=AuthorityClass.EVENT,
        evidence=(quantity_candidate.evidence,),
        candidate_ids=(quantity_candidate.candidate_id,),
        quantity=quantity,
    )
    decision = AdjudicationDecisionV1(
        decision_id="d1",
        action=AdjudicationAction.ACCEPT,
        candidate_ids=(quantity_candidate.candidate_id,),
        resulting_atom_ids=(atom.atom_id,),
        adjudicator_identity="owner",
        decided_at=datetime(2026, 8, 22, tzinfo=UTC),
        rationale="exact complete quantity",
    )
    provisional = AdjudicationReceiptV1(decisions=(decision,), receipt_identity=ZERO)
    receipt = provisional.model_copy(
        update={"receipt_identity": canonical_identity(provisional)}
    )
    revised = apply_adjudication(prior=prior, receipt=receipt, resulting_atoms=(atom,))
    assert revised.revision == 2 and revised.atoms == (atom,)
    assert revised.adjudication_receipt_identities == (receipt.receipt_identity,)


def test_canonical_atomic_round_trip_and_stale_revision_fail_closed(tmp_path: Path):
    draft = _draft()
    bundle = _bundle(draft)
    store = VoiceFactAtomBundleStoreV1(tmp_path / "atoms.json")
    first = store.save(bundle, draft=draft)
    assert store.load(draft=draft) == bundle
    assert first == canonical_identity(bundle)
    stale = _draft("Autoritatea a publicat raportul.")
    with pytest.raises(FactAtomBundleIntegrityError, match="stale"):
        store.load(draft=stale)


def test_unknown_version_fails_closed(tmp_path: Path):
    draft = _draft()
    bundle = _bundle(draft)
    path = tmp_path / "atoms.json"
    path.write_text(
        json.dumps(bundle.model_dump(mode="json") | {"schema_version": "999"}),
        encoding="utf-8",
    )
    with pytest.raises(UnknownFactAtomBundleVersionError):
        VoiceFactAtomBundleStoreV1(path).load(draft=draft)


def test_ambiguous_candidate_cannot_become_an_atom_without_receipt():
    draft = _draft()
    candidate = extract_surface_candidates(
        authority_class=AuthorityClass.EVENT,
        authority_identity=_sha("authority"),
        source_identity="s",
        text="Primarul a semnat proiectul",
    )[0]
    bundle = _bundle(draft, (candidate,))
    assert bundle.atoms == () and candidate.requires_semantic_adjudication
