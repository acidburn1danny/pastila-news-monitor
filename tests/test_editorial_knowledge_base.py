"""Editorial knowledge contract, builder, relationship, and evidence tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.controlled_revision_quality.editorial_knowledge import (
    Confidence,
    EditorialKnowledgeBase,
    FindingType,
    KnowledgeRelationship,
    KnowledgeStatus,
    RelationshipType,
    deserialize_knowledge_base,
    duplicate_findings,
    entry_fingerprint,
    knowledge_base_fingerprint,
    serialize_knowledge_base,
    validate_knowledge_base,
)
from scripts.build_editorial_knowledge_base import (
    INDEX_PATH,
    KNOWLEDGE_PATH,
    build_index,
    build_knowledge_base,
)

ROOT = Path.cwd()


def _base() -> EditorialKnowledgeBase:
    return build_knowledge_base(ROOT)


def test_initial_knowledge_base_constructs_and_validates():
    base = _base()
    diagnostics = validate_knowledge_base(base, ROOT)

    assert len(base.entries) == 8
    assert diagnostics.valid
    assert diagnostics.entries_validated == 8
    assert diagnostics.duplicate_findings == 0
    assert diagnostics.artifacts_validated > 0


def test_serialization_deserialization_round_trip(tmp_path: Path):
    path = tmp_path / "knowledge.json"
    base = _base()
    serialize_knowledge_base(path, base)

    assert deserialize_knowledge_base(path) == base


def test_entry_and_base_fingerprints_are_deterministic():
    first = _base()
    second = _base()

    assert first.knowledge_base_fingerprint == second.knowledge_base_fingerprint
    assert first.knowledge_base_fingerprint == knowledge_base_fingerprint(first)
    assert all(
        item.entry_fingerprint == entry_fingerprint(item) for item in first.entries
    )


def test_duplicate_knowledge_ids_are_rejected():
    base = _base()
    with pytest.raises(ValidationError, match="duplicate knowledge IDs"):
        EditorialKnowledgeBase.model_validate(
            {
                **base.model_dump(mode="json"),
                "entries": [*base.entries, base.entries[0]],
            }
        )


def test_duplicate_findings_are_detected_independently_of_ids():
    base = _base()
    duplicate = base.entries[0].model_copy(update={"knowledge_id": "EK-099"})

    assert duplicate_findings((*base.entries, duplicate)) == 1


@pytest.mark.parametrize("confidence", ["CERTAIN", "PROBABLE"])
def test_invalid_confidence_is_rejected(confidence: str):
    data = _base().entries[0].model_dump(mode="json")
    data["confidence"] = confidence
    with pytest.raises(ValidationError):
        type(_base().entries[0]).model_validate(data)


def test_invalid_finding_type_is_rejected():
    data = _base().entries[0].model_dump(mode="json")
    data["finding_type"] = "IDEA"
    with pytest.raises(ValidationError):
        type(_base().entries[0]).model_validate(data)


def test_invalid_status_is_rejected():
    data = _base().entries[0].model_dump(mode="json")
    data["status"] = "DRAFT"
    with pytest.raises(ValidationError):
        type(_base().entries[0]).model_validate(data)


def test_broken_relationship_is_rejected():
    base = _base()
    relationship = KnowledgeRelationship(
        source_id="EK-001",
        target_id="EK-999",
        relationship_type=RelationshipType.RELATED_TO,
        explanation="broken test reference",
    )
    with pytest.raises(ValidationError, match="broken relationship"):
        EditorialKnowledgeBase.model_validate(
            {**base.model_dump(mode="json"), "relationships": [relationship]}
        )


def test_circular_supersession_is_rejected():
    base = _base()
    first = base.entries[0].model_copy(
        update={
            "status": KnowledgeStatus.SUPERSEDED,
            "superseded_by": "EK-002",
        }
    )
    second = base.entries[1].model_copy(
        update={
            "status": KnowledgeStatus.SUPERSEDED,
            "superseded_by": "EK-001",
        }
    )
    with pytest.raises(ValidationError, match="circular supersession"):
        EditorialKnowledgeBase.model_validate(
            {
                **base.model_dump(mode="json"),
                "entries": [first, second, *base.entries[2:]],
            }
        )


def test_missing_manifest_is_detected():
    base = _base()
    evidence = (
        base.entries[0]
        .supporting_evidence[0]
        .model_copy(update={"manifest_path": "docs/artifacts/missing-manifest.json"})
    )
    entry = base.entries[0].model_copy(update={"supporting_evidence": (evidence,)})
    changed = base.model_copy(update={"entries": (entry, *base.entries[1:])})

    assert any(
        "missing evidence artifact" in item
        for item in validate_knowledge_base(changed, ROOT).errors
    )


def test_missing_evidence_artifact_is_detected():
    base = _base()
    evidence = (
        base.entries[0]
        .supporting_evidence[0]
        .model_copy(
            update={"artifact_paths": ("docs/artifacts/missing-evidence.json",)}
        )
    )
    entry = base.entries[0].model_copy(update={"supporting_evidence": (evidence,)})
    changed = base.model_copy(update={"entries": (entry, *base.entries[1:])})

    assert not validate_knowledge_base(changed, ROOT).valid


def test_fingerprint_mismatch_is_detected():
    base = _base().model_copy(update={"knowledge_base_fingerprint": "0" * 64})

    assert (
        "knowledge base fingerprint mismatch"
        in validate_knowledge_base(base, ROOT).errors
    )


def test_manifest_and_tradeoff_linkage_is_present_for_every_entry():
    base = _base()

    assert all(item.supporting_evidence for item in base.entries)
    assert all(
        evidence.manifest_path.endswith("experiment-manifest.json")
        for item in base.entries
        for evidence in item.supporting_evidence
    )
    assert any(
        any(
            path.endswith("causal-editorial-tradeoff-analysis.json")
            for path in evidence.artifact_paths
        )
        for item in base.entries
        for evidence in item.supporting_evidence
    )


def test_relationship_vocabulary_and_counts():
    base = _base()
    counts = {kind: 0 for kind in RelationshipType}
    for relationship in base.relationships:
        counts[relationship.relationship_type] += 1

    assert counts == {
        RelationshipType.SUPPORTS: 1,
        RelationshipType.REFINES: 3,
        RelationshipType.CONTRADICTS: 0,
        RelationshipType.SUPERSEDES: 0,
        RelationshipType.DEPENDS_ON: 1,
        RelationshipType.RELATED_TO: 1,
    }


def test_index_is_deterministic_and_query_ready():
    first = build_index(_base())
    second = build_index(_base())

    assert first == second
    assert "EK-001" in first["by_category"]["QUOTE_MUTATION"]
    assert "EK-002" in first["by_scenario"]["SYN-20"]
    assert first["by_confidence"][Confidence.HIGH.value]
    assert first["by_finding_type"][FindingType.BEST_PRACTICE.value]


def test_checked_in_base_and_index_match_builder():
    checked = deserialize_knowledge_base(KNOWLEDGE_PATH)
    rebuilt = _base()
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

    assert checked == rebuilt
    assert index == build_index(rebuilt)


def test_knowledge_base_contains_no_secrets_or_absolute_paths():
    text = json.dumps(_base().model_dump(mode="json"), ensure_ascii=False).casefold()
    for forbidden in (
        "api_key",
        "access_token",
        "bearer ",
        "authorization_header",
        "c:\\users\\",
    ):
        assert forbidden not in text


def test_all_entries_are_active_reusable_evidence_not_ideas():
    base = _base()

    assert all(item.status == KnowledgeStatus.ACTIVE for item in base.entries)
    assert all(item.reusable and not item.deprecated for item in base.entries)
    assert all(item.finding_type in FindingType for item in base.entries)


def test_h3_appends_immutable_refinement_without_rewriting_ek002():
    base = _base()
    ek002 = next(item for item in base.entries if item.knowledge_id == "EK-002")
    ek008 = next(item for item in base.entries if item.knowledge_id == "EK-008")

    assert ek002.net_editorial_utility == -2
    assert ek008.net_editorial_utility == 8
    assert ek008.source_experiments == ("20260728-161607-openai-gpt-4.1-mini-7h4",)
    assert any(
        item.source_id == "EK-008"
        and item.target_id == "EK-002"
        and item.relationship_type == RelationshipType.REFINES
        for item in base.relationships
    )
