from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from pastila_scout.voice_fact_atoms_v2 import (
    TypedAuthorityFieldInputV2,
    VoiceFactAtomBundleV2,
    canonical_bytes,
    extract_surface_candidates,
    extract_typed_authority_candidates_v2,
    finalize_bundle_identity,
)
from pastila_scout.voice_fact_atoms_v2.models import AuthorityClass

AUTHORITY = "authority:story"


def _field(name: str, text: str, *, article_id: int = 7):
    return TypedAuthorityFieldInputV2(
        authority_class=AuthorityClass.EVENT,
        authority_identity=AUTHORITY,
        article_id=article_id,
        source_id="source",
        field_name=name,
        text=text,
        text_sha256="sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def test_v2_extracts_title_and_summary_independently_without_scaffolding():
    title = _field("title", "Titlu George Smyth")
    summary = _field("summary", "Rezumat 18 ani")
    candidates = extract_typed_authority_candidates_v2((title, summary))
    assert {item.evidence.source_identity for item in candidates} == {
        "article:7:source:field:title",
        "article:7:source:field:summary",
    }
    assert {item.evidence.passage for item in candidates} == {
        "Titlu George Smyth",
        "Rezumat",
        "18 ani",
    }
    assert all("Sursa" not in item.evidence.passage for item in candidates)
    assert all("Publicat" not in item.evidence.passage for item in candidates)
    assert all("Statut extras" not in item.evidence.passage for item in candidates)
    assert all("\n" not in item.evidence.passage for item in candidates)


def test_renderer_only_changes_cannot_change_v2_identity():
    fields = (_field("title", "George Smyth"), _field("summary", "18 ani"))
    before = extract_typed_authority_candidates_v2(fields)
    renderer_variants = (
        "Sursa: source\nTitlu: ...\nRezumat: ...",
        "SOURCE\nSUMMARY RENAMED\nPublicat moved\nExtra metadata",
    )
    assert renderer_variants[0] != renderer_variants[1]
    after = extract_typed_authority_candidates_v2(fields)
    assert tuple(item.candidate_id for item in before) == tuple(
        item.candidate_id for item in after
    )


def test_field_and_occurrence_are_identity_inputs_and_policy_is_v2():
    text = "18 ani și 18 ani"
    title = _field("title", text)
    summary = _field("summary", text)
    candidates = extract_typed_authority_candidates_v2((title, summary))
    assert len(candidates) == 4
    assert len({item.candidate_id for item in candidates}) == 4
    assert {item.evidence.start for item in candidates} == {0, 10}
    v1 = extract_surface_candidates(
        authority_class=AuthorityClass.EVENT,
        authority_identity=AUTHORITY,
        source_identity=title.source_identity,
        text=text,
    )
    assert {item.candidate_id for item in v1}.isdisjoint(
        item.candidate_id for item in candidates
    )


def test_typed_field_contract_rejects_unknown_version_and_bad_hash():
    payload = _field("title", "George Smyth").model_dump(mode="json")
    with pytest.raises(ValidationError):
        TypedAuthorityFieldInputV2.model_validate(payload | {"schema_version": "999"})
    with pytest.raises(ValidationError, match="identity mismatch"):
        TypedAuthorityFieldInputV2.model_validate(
            payload | {"text_sha256": "sha256:" + "0" * 64}
        )


def test_v2_bundle_round_trip_is_canonical_and_unknown_policy_fails_closed():
    candidate = extract_typed_authority_candidates_v2((_field("summary", "18 ani"),))[0]
    bundle = finalize_bundle_identity(
        VoiceFactAtomBundleV2(
            revision=1,
            semantic_draft_revision_identity="sha256:" + "1" * 64,
            event_id=7,
            story_position=1,
            factual_summary_identity="sha256:" + "2" * 64,
            event_authority_identity=AUTHORITY,
            candidates=(candidate,),
            atoms=(),
            bundle_identity="sha256:" + "0" * 64,
        )
    )
    raw = canonical_bytes(bundle)
    loaded = VoiceFactAtomBundleV2.model_validate_json(raw)
    assert canonical_bytes(loaded) == raw
    assert loaded.bundle_identity == bundle.bundle_identity
    with pytest.raises(ValidationError):
        VoiceFactAtomBundleV2.model_validate(
            bundle.model_dump(mode="json")
            | {"extraction_policy_version": "unknown-policy"}
        )
