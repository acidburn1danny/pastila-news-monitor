import importlib.util
import json
from pathlib import Path


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path); value = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(value); return value


C = module("scripts/calibrate_editor_vnext_minimal_source_bound_verifier_closed_evidence_v1.py", "calibration")
V = module("scripts/run_editor_vnext_minimal_source_bound_verifier_diagnostic_v1.py", "verifier")
E = json.loads(Path("docs/artifacts/editor-vnext-minimal-source-bound-verifier-closed-evidence-v1.json").read_text(encoding="utf-8"))


def test_closed_evidence_identity_and_inventory():
    C.verify_identity(E, "input_identity")
    assert len(E["rows"]) == 48
    assert all(len(x["r2_output_sha256"]) == 64 for x in E["rows"])
    assert len({x["case_id"] for x in E["rows"]}) == 48


def test_calibration_preserves_evidence_limitations():
    result = C.run(E, V)
    assert result["status"] == "PASS_WITH_EVIDENCE_LIMITATIONS"
    assert result["decision"] == "REVISE_BEFORE_ACTIVE_INTEGRATION"
    assert result["verifier_miss_rate_estimable"] is False
    assert result["change_cause_distribution"] == {"EVIDENCE_INSUFFICIENT_DIFFERENT_OUTPUT_BYTES": 48}
    assert result["fallback_comparison"]["causal_comparison_valid"] is False


def test_no_false_claim_from_human_positive_only_cohort():
    result = C.run(E, V)
    assert result["true_model_failures_demonstrated"] == []
    assert result["false_rejections"] == []
    assert result["observed_verifier_misses"] == []
    assert result["verdict_distribution"] == {"PASS_PROVEN": 45, "UNPROVEN": 3}


def test_output_tampering_fails_closed():
    altered = json.loads(json.dumps(E)); altered["rows"][0]["r2_output"] += " schimbat"
    altered.pop("input_identity")
    altered["input_identity"] = C.digest(C.canonical(altered))
    try: C.run(altered, V)
    except ValueError as exc: assert "closed output drift" in str(exc)
    else: raise AssertionError("tampered closed output accepted")


def test_source_packet_and_score_closure_tampering_fail_closed():
    altered = json.loads(json.dumps(E)); altered["rows"][0]["source_packet"]["spans"][0]["text"] += " schimbat"
    altered.pop("input_identity"); altered["input_identity"] = C.digest(C.canonical(altered))
    try: C.run(altered, V)
    except ValueError as exc: assert "source packet byte binding" in str(exc) or "identity mismatch" in str(exc)
    else: raise AssertionError("tampered source packet accepted")

    altered = json.loads(json.dumps(E)); altered["rows"][0]["human_score_receipt"]["receipt_identity"] = "0" * 64
    altered.pop("input_identity"); altered["input_identity"] = C.digest(C.canonical(altered))
    try: C.run(altered, V)
    except ValueError as exc: assert "human score closure mismatch" in str(exc)
    else: raise AssertionError("score receipt outside closure accepted")
