import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/artifacts/semantic-admission-v2-gate-f-v2-4-residual-failure-design-v1.json"


def test_residual_design_preserves_case_01_and_exact_case_10_contract() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    assert design["preserve_success"]["case_id"] == "HMCV1-SASC-01"
    required = design["residual_case"]["required_classification"]
    assert required["decisive"] == ["FSEM_CERTAINTY_MUTATION"]
    assert required["supporting"] == ["FSEM_TIMING_MUTATION", "FSEM_UNSUPPORTED_LIFE_STAKES"]


def test_residual_design_requires_delta_first_and_negative_evidence() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    remediation = design["bounded_remediation_requirements"]
    assert any("Compare matched event axes" in item for item in remediation["delta_first_analysis"])
    assert any("Do not emit FSEM_UNSUPPORTED_MOTIVE_OR_INTENT" in item for item in remediation["negative_evidence_for_open_classes"])
    assert any("does not itself supply real intent or causality" in item for item in remediation["negative_evidence_for_open_classes"])


def test_residual_design_requires_source_side_span_membership_without_repair() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    grounding = design["bounded_remediation_requirements"]["span_grounding"]
    assert any("candidate_span must be a byte-exact contiguous substring" in item for item in grounding)
    assert any("authority_support must be a byte-exact contiguous substring" in item for item in grounding)
    assert "SPAN_REPAIR_OR_SUBSTITUTION" in design["prohibited"]


def test_residual_design_grants_no_candidate_or_inference_authority() -> None:
    design = json.loads(SPEC.read_text("utf-8"))
    assert design["authority"] == {
        "candidate_implementation": False,
        "inference": False,
        "runtime": False,
        "training": False,
        "gate_s": False,
    }
