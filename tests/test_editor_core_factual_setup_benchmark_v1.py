import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_editor_core_factual_setup_benchmark_v1 import audit  # noqa: E402
from build_editor_core_factual_setup_benchmark_v1 import build  # noqa: E402
from evaluate_editor_core_factual_setup_benchmark_v1 import validate_generated_response  # noqa: E402
from score_editor_core_factual_setup_comparison_v1 import sign_test  # noqa: E402


def test_builder_is_byte_exact(tmp_path, monkeypatch):
    import build_editor_core_factual_setup_benchmark_v1 as module

    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    contract = ROOT / "docs/artifacts/editor-core-factual-setup-contract-v1.json"
    (artifact_root / contract.name).write_bytes(contract.read_bytes())
    monkeypatch.setattr(module, "ART", artifact_root)
    monkeypatch.setattr(module, "ROOT", ROOT)
    built = build()
    for name in ("requests.jsonl", "answer-key.jsonl", "manifest.json"):
        expected = ROOT / "docs" / "artifacts" / f"editor-core-factual-setup-benchmark-v1-{name}"
        assert (artifact_root / f"editor-core-factual-setup-benchmark-v1-{name}").read_bytes() == expected.read_bytes()
    assert built["cases"] == 24


def test_full_audit_passes_and_excludes_historical_holdouts():
    result = audit()
    assert result["status"] == "PASS"
    assert result["cases"] == result["multisource_cases"] == 24
    assert result["unique_spans"] == 72
    assert result["historical_holdouts_read"] is False
    assert result["voice_comedy_polish_objective"] is False


def test_requests_are_blind_and_keys_are_separate():
    request_path = ROOT / "docs/artifacts/editor-core-factual-setup-benchmark-v1-requests.jsonl"
    key_path = ROOT / "docs/artifacts/editor-core-factual-setup-benchmark-v1-answer-key.jsonl"
    requests = request_path.read_text(encoding="utf-8")
    keys = [json.loads(line) for line in key_path.read_bytes().splitlines()]
    assert "assistant_target" not in requests
    assert len(keys) == 24
    assert all(row["assistant_target"] not in requests for row in keys)


def test_audit_fails_on_target_mutation(tmp_path, monkeypatch):
    import audit_editor_core_factual_setup_benchmark_v1 as module

    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    for source in (ROOT / "docs/artifacts").glob("editor-core-factual-setup-*.json*"):
        (artifact_root / source.name).write_bytes(source.read_bytes())
    target = artifact_root / "editor-core-factual-setup-benchmark-v1-requests.jsonl"
    target.write_bytes(target.read_bytes() + b"\n")
    monkeypatch.setattr(module, "ART", artifact_root)
    monkeypatch.setattr(module, "CONTRACT", artifact_root / "editor-core-factual-setup-contract-v1.json")
    with pytest.raises(ValueError):
        module.audit()


def test_same_source_may_support_multiple_claims_and_order_is_not_semantic():
    payload = {
        "case_id": "fixture", "request_identity": "sha256:" + "a" * 64,
        "output_type": "FACTUAL", "authority_spans": [
            {"span_id": "s1"}, {"span_id": "s2"}, {"span_id": "s3"}],
    }
    value = {
        "schema": "pastila-core-v2-structured-qualification-response", "schema_version": 2,
        "case_id": "fixture", "request_identity": payload["request_identity"], "output_type": "FACTUAL",
        "outcome": "ANSWER", "text": "Prima propoziție este factuală. A doua rămâne factuală.",
        "claim_bindings": [
            {"claim_index": 1, "source_span_ids": ["s2", "s1"]},
            {"claim_index": 2, "source_span_ids": ["s1", "s3"]},
        ], "abstention_code": None,
    }
    assert validate_generated_response(json.dumps(value, ensure_ascii=False, separators=(",", ":")), payload, True) == value


def test_predeclared_sign_test_and_closed_comparison_result():
    result = json.loads(
        (ROOT / "docs/artifacts/editor-core-factual-setup-comparison-v1-result.json").read_text(encoding="utf-8")
    )
    assert sign_test(4, 1) == 0.1875
    assert (result["r2_wins"], result["r1_wins"], result["ties"]) == (4, 1, 19)
    assert result["r2_safety_regressions"] == 0
    assert result["selection_rule_pass"] is False
    assert result["development_parent_conclusion"] == "R2_STEP_9_RETAINS_OPERATIONALLY_NO_SUPERIORITY_CLAIM"
    assert result["historical_holdouts_opened"] is False
    assert result["training_performed"] is False
