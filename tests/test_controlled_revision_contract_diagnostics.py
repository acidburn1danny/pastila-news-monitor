from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.diagnose_controlled_revision_contract import analyze, main


def _history_digest() -> str:
    return hashlib.sha256(
        Path("docs/artifacts/controlled-provider-quality-history.json").read_bytes()
    ).hexdigest()


def test_all_frozen_scenarios_and_categories_are_analyzed() -> None:
    artifact = analyze()
    assert artifact["scenario_count"] == 24
    assert artifact["category_count"] == 12
    assert len(artifact["scenario_diagnostics"]) == 24


def test_every_failure_is_localized_and_classified() -> None:
    records = analyze()["scenario_diagnostics"]
    assert all(item["failure_stage"] for item in records)
    assert all(item["first_deterministic_failure"] for item in records)
    assert all(item["responsible_validator"] for item in records)
    assert all(item["responsible_contract"] for item in records)
    assert all(item["corrected_failure_class"] for item in records)


def test_missing_provider_reference_values_are_reported_not_invented() -> None:
    artifact = analyze()
    assert all(
        item["provider_produced_references"] is None
        and item["reference_precision"] is None
        and item["reference_recall"] is None
        for item in artifact["scenario_diagnostics"]
    )
    aggregate = artifact["aggregate_diagnostics"]
    assert aggregate["reference_frequency_table"] is None
    assert aggregate["reference_confusion_matrix"] is None


def test_failure_counts_and_stages_are_internally_consistent() -> None:
    artifact = analyze()
    aggregate = artifact["aggregate_diagnostics"]
    assert sum(aggregate["failure_frequency"].values()) == 24
    assert sum(aggregate["failure_stage_distribution"].values()) == 24
    assert aggregate["failure_clusters"] == {
        "reference_contract_rejection": 23,
        "provider_dto_schema_rejection": 1,
    }


def test_prompt_schema_authorization_and_runner_findings_are_explicit() -> None:
    artifact = analyze()
    assert artifact["prompt_analysis"]["clearly_specifies_reference_requirements"]
    assert not artifact["schema_analysis"][
        "invocation_specific_reference_values_constrained"
    ]
    assert artifact["authorization_analysis"]["rejects_invalid_references"]
    assert not artifact["runner_analysis"]["failure_classification_correct"]
    assert artifact["root_conclusion"] == "INSUFFICIENT_EVIDENCE"
    assert artifact["final_recommendation"] == "FIX_RUNNER_ONLY"


def test_analysis_and_artifact_generation_leave_history_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    before = _history_digest()
    output = tmp_path / "diagnostics.json"
    monkeypatch.setattr("scripts.diagnose_controlled_revision_contract.OUTPUT", output)
    assert main() == 0
    assert _history_digest() == before
    assert json.loads(output.read_text(encoding="utf-8"))["provider_requests"] == 0


def test_artifact_contains_no_provider_prompt_or_episode_content() -> None:
    payload = json.dumps(analyze(), ensure_ascii=False).casefold()
    forbidden = (
        "source_draft",
        "assembled_text",
        "revision_instruction",
        "response_body",
        "api_key",
        "bearer ",
    )
    assert not any(value in payload for value in forbidden)


def test_checked_in_artifact_matches_deterministic_analysis() -> None:
    checked_in = json.loads(
        Path("docs/artifacts/controlled-revision-contract-diagnostics.json").read_text(
            encoding="utf-8"
        )
    )
    current = analyze()
    # Part 7D is immutable historical evidence; later baseline history appends do not
    # retroactively change the number of entries it analyzed.
    current["history_entries_analyzed"] = checked_in["history_entries_analyzed"]
    assert checked_in == current
