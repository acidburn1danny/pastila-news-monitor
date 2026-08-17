from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime

import pytest

from pastila_scout.editorial_evidence_v1 import (
    EditClassV1,
    EditorialEvidenceStoreV1,
    EvidenceStoreErrorV1,
    LearnabilityV1,
    OwnerClassificationV1,
    aggregate_episode_v1,
    analyze_pair_v1,
    render_observation_report_v1,
)
from pastila_scout.editorial_evidence_v1.analysis import structured_diff_v1
from pastila_scout.editorial_evidence_v1.models import CaptureMetadataV1


def metadata() -> CaptureMetadataV1:
    return CaptureMetadataV1(
        project_id="active-project-v1:test",
        event_id=29,
        component_id="story:event:29",
        provider="ollama",
        model="qwen3:14b",
        prompt_identity="prompt:v1",
        policy_identity="policy:v1",
        catalog_identity="catalog:v1",
        retrieved_tool_ids=(),
        generation_attempt=1,
    )


def test_generated_snapshot_is_idempotent_immutable_and_finalization_is_explicit(
    tmp_path,
):
    store = EditorialEvidenceStoreV1(tmp_path)
    first = store.capture_generated(
        metadata=metadata(),
        text="Prima frază. A doua frază.",
        captured_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    assert (
        store.capture_generated(
            metadata=metadata(), text=first.generated.text
        ).capture_id
        == first.capture_id
    )
    final = store.finalize(
        first.capture_id,
        final_text="Prima frază. A doua frază schimbată.",
        finalization_source="owner_explicit_finalize",
    )
    assert final.generated == first.generated and final.final is not None
    assert (
        store.finalize(
            first.capture_id,
            final_text=final.final.text,
            finalization_source="repeated_save",
        )
        == final
    )
    with pytest.raises(EvidenceStoreErrorV1, match="already finalized"):
        store.finalize(
            first.capture_id,
            final_text="Alt final.",
            finalization_source="owner_explicit_finalize",
        )


def test_structured_diff_is_deterministic_and_detects_move_insert_delete_and_edit():
    generated = "Unu. Doi. Trei."
    final = "Doi. Unu. Patru."
    first = structured_diff_v1(generated, final)
    assert first == structured_diff_v1(generated, final)
    assert {item.operation.value for item in first} >= {"MOVED", "DELETED", "INSERTED"}
    edited = structured_diff_v1("Unu este aici.", "Unu este chiar aici.")
    assert edited[0].operation.value == "LIGHT_EDIT"


def test_kpi_partial_score_never_substitutes_unavailable_dimensions():
    diff, kpi = analyze_pair_v1(
        "Text factual. Altă frază.", "Text factual schimbat. Altă frază."
    )
    assert diff and kpi.score is not None
    assert not kpi.dimensions["M"].available and kpi.dimensions["M"].value is None
    assert not kpi.dimensions["F"].available and kpi.dimensions["F"].value is None
    assert not kpi.dimensions["T"].available and kpi.dimensions["T"].value is None
    assert kpi.completeness == pytest.approx(0.60)


def test_owner_fact_and_hallucination_classes_are_separate_and_penalized():
    classes = (
        OwnerClassificationV1(
            diff_index=0,
            edit_class=EditClassV1.REMOVE_HALLUCINATION,
            learnability=LearnabilityV1.FACT_ONLY,
        ),
    )
    _, kpi = analyze_pair_v1("Primarul a furat sigur.", "Există o anchetă.", classes)
    assert kpi.dimensions["F"].value == 0 and kpi.critical_factual_issue
    assert kpi.classification_coverage == 1


def test_style_classification_does_not_claim_factual_safety_until_coverage_complete():
    classes = (
        OwnerClassificationV1(
            diff_index=0,
            edit_class=EditClassV1.STYLE_OR_VOICE,
            learnability=LearnabilityV1.STYLE_CANDIDATE,
        ),
    )
    _, kpi = analyze_pair_v1("Prima. A doua.", "Prima schimbată. Alta.", classes)
    assert not kpi.dimensions["F"].available


def test_store_detects_truncation_malformed_schema_and_hash_mismatch(tmp_path):
    store = EditorialEvidenceStoreV1(tmp_path)
    captured = store.capture_generated(metadata=metadata(), text="Text inițial.")
    path = next(tmp_path.glob("*.json"))
    original = path.read_text(encoding="utf-8")
    for corrupt in (
        "{",
        json.dumps({"schema_version": 1}),
        original.replace("Text inițial", "Text înlocuit"),
    ):
        path.write_text(corrupt, encoding="utf-8")
        with pytest.raises(EvidenceStoreErrorV1):
            store.require(captured.capture_id)
    path.write_text(original, encoding="utf-8")
    assert store.require(captured.capture_id) == captured


def test_invalid_files_are_skipped_without_losing_valid_owner_evidence(tmp_path):
    store = EditorialEvidenceStoreV1(tmp_path)
    captured = store.capture_generated(metadata=metadata(), text="Text valid.")
    bad = tmp_path / f"{'f' * 64}.json"
    bad.write_text("truncated", encoding="utf-8")
    assert store.list_valid() == (captured,)
    assert bad.exists()


def test_owner_can_correct_classification_and_delete_or_reset(tmp_path):
    store = EditorialEvidenceStoreV1(tmp_path)
    captured = store.capture_generated(metadata=metadata(), text="Fraza lungă inutilă.")
    finalized = store.finalize(
        captured.capture_id, final_text="Fraza utilă.", finalization_source="owner"
    )
    corrected = store.correct_classifications(
        captured.capture_id,
        (
            OwnerClassificationV1(
                diff_index=0,
                edit_class=EditClassV1.STYLE_OR_VOICE,
                learnability=LearnabilityV1.ONE_OFF,
            ),
        ),
    )
    assert (
        corrected.classifications[0].owner_confirmed and corrected.kpi != finalized.kpi
    )
    assert store.delete(captured.capture_id) and store.list_valid() == ()
    store.capture_generated(metadata=metadata(), text="Alt text.")
    assert store.reset() == 1


def test_episode_aggregate_uses_story_scores_not_tiny_unit_counts():
    _, left = analyze_pair_v1("A. B.", "A. B.")
    _, right = analyze_pair_v1("C. D.", "Complet diferit.")
    result = aggregate_episode_v1((left, right))
    assert result["measured_story_count"] == 2 and result["median_score"] is not None


def test_analysis_is_provider_neutral_and_observation_only():
    left = metadata()
    right = left.model_copy(update={"provider": "openai", "model": "gpt-future"})
    a = analyze_pair_v1("Aceeași intrare.", "Același final.")
    b = analyze_pair_v1("Aceeași intrare.", "Același final.")
    assert a == b and left.provider != right.provider
    assert not hasattr(EditorialEvidenceStoreV1, "promote")
    assert not hasattr(EditorialEvidenceStoreV1, "guidance")


def test_owner_report_exposes_baseline_final_diff_kpi_and_no_preferences(tmp_path):
    store = EditorialEvidenceStoreV1(tmp_path)
    captured = store.capture_generated(metadata=metadata(), text="Textul dat de Scout.")
    final = store.finalize(
        captured.capture_id,
        final_text="Textul final al proprietarului.",
        finalization_source="owner_explicit_finalize",
    )
    report = render_observation_report_v1(final)
    assert (
        "Textul dat de Scout" in report and "Textul final al proprietarului" in report
    )
    assert "Diferențe" in report and "Completitudine" in report
    assert "preferin" not in report.casefold()


def test_governed_editor_export_capture_checks_identity_and_provenance(tmp_path):
    envelope = {
        "schema_name": "pastila-editor-operational-export",
        "schema_version": "1",
        "operational_result": {
            "status": "completed",
            "execution_request_fingerprint": "request:fingerprint",
            "preparation_result_fingerprint": "policy:fingerprint",
            "attempt_count": 1,
            "generation_manifest": {
                "provider": "ollama",
                "model_identifier": "qwen3:14b",
            },
            "draft": {"assembled_text": "Text românesc generat.", "usage_receipts": []},
        },
        "payload_sha256": "",
    }
    canonical = (
        json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    envelope["payload_sha256"] = digest
    path = tmp_path / "editor.json"
    path.write_text(
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    captured = EditorialEvidenceStoreV1(tmp_path / "evidence").capture_editor_output(
        path=path, expected_payload_sha256=digest, project_id="project", event_id=29
    )
    assert captured.generated.text == "Text românesc generat."
    assert (
        captured.metadata.provider == "ollama"
        and captured.metadata.model == "qwen3:14b"
    )
    with pytest.raises(EvidenceStoreErrorV1, match="identity"):
        EditorialEvidenceStoreV1(tmp_path / "other").capture_editor_output(
            path=path,
            expected_payload_sha256="sha256:" + "0" * 64,
            project_id="project",
            event_id=29,
        )


def test_interrupted_atomic_replace_leaves_no_partial_record(tmp_path, monkeypatch):
    store = EditorialEvidenceStoreV1(tmp_path)
    monkeypatch.setattr(
        os, "replace", lambda *args: (_ for _ in ()).throw(OSError("interrupted"))
    )
    with pytest.raises(OSError, match="interrupted"):
        store.capture_generated(metadata=metadata(), text="Text protejat.")
    assert tuple(tmp_path.iterdir()) == ()


def test_representative_romanian_analysis_is_bounded():
    generated = " ".join(
        f"Fraza {index} descrie clar evenimentul." for index in range(120)
    )
    final = generated.replace("clar", "concis")
    started = time.perf_counter()
    diff, kpi = analyze_pair_v1(generated, final)
    assert len(diff) == 120 and kpi.score is not None
    assert time.perf_counter() - started < 1.0
