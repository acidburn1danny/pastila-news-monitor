import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-case01-v4-failure-analysis-remediation-design-v1.json"


def _design() -> dict:
    return json.loads(DESIGN.read_text("utf-8"))


def test_design_is_bound_to_single_probe_and_has_no_authority() -> None:
    value = _design()
    assert value["source_probe_identity"] == "d6e0cb249b54ff188cf70995a7e7d848819ccc6eef3257a1bef1528005e17859"
    assert value["lifecycle"] == "DESIGN_ONLY_READY_FOR_OWNER_REVIEW"
    assert not any(value["authority"].values())


def test_remediation_preserves_creative_and_embedded_proposition_boundary() -> None:
    value = _design()["remediation_candidate"]
    assert "never immunizes" in value["embedded_proposition_safety"]
    delta = " ".join(value["contract_delta"])
    assert "factual-return test" in delta
    assert "CONTAINED_CREATIVE" in delta
    assert "UNRESOLVED_SCOPE" in delta


def test_next_step_stops_before_inference_and_stage_c() -> None:
    value = _design()
    assert "zero-inference" in value["bounded_next_step_if_authorized"]
    assert "Stop before any model probe" in value["bounded_next_step_if_authorized"]
    checks = " ".join(value["zero_inference_verification_contract"])
    assert "Stage C" in checks and "model" in checks and "inference" in checks
