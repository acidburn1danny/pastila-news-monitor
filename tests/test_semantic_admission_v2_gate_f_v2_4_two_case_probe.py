import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_probe_is_exactly_two_gate_f_only_calls() -> None:
    plan = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-gate-f-v2-4-two-case-probe-v1.json").read_text("utf-8"))
    assert plan["case_ids"] == ["HMCV1-SASC-01", "HMCV1-SASC-10"]
    assert plan["gate_id"] == "FACTUAL_SEMANTIC"
    assert plan["maximum_provider_calls"] == 2
    assert plan["attempts_per_case"] == 1
    assert plan["gate_s_included"] is False
    assert plan["silent_retry"] is plan["repair"] is plan["selection"] is False


def test_probe_runner_persists_each_raw_call_and_grants_no_runtime_authority() -> None:
    source = (ROOT / "scripts/run_semantic_admission_v2_gate_f_v2_4_two_case_probe_v1.py").read_text("utf-8")
    assert "_write(ledger_path, ledger)" in source
    assert '"maximum_provider_calls") != 2' in source
    assert '"gate_s_included": False' in source
    assert '"runtime_authority": False' in source


def test_sealed_probe_preserves_exact_nonconformance() -> None:
    out = ROOT / ".semantic-admission-v2-gate-f-v2-4-contract-probe-v1-evidence"
    if not (out / "evaluation-summary.json").exists():
        return
    summary = json.loads((out / "evaluation-summary.json").read_text("utf-8"))
    assert summary["case_results"][0]["result"] == "EXACT_PASS"
    case_10 = summary["case_results"][1]
    assert case_10["missing_required_codes"] == ["FSEM_CERTAINTY_MUTATION", "FSEM_TIMING_MUTATION"]
    assert case_10["spurious_codes"] == ["FSEM_UNSUPPORTED_CAUSALITY", "FSEM_UNSUPPORTED_MOTIVE_OR_INTENT"]
    assert summary["probe_acceptance_passed"] is False
    assert summary["full_ten_case_run_eligible"] is False
