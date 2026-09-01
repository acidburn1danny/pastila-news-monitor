import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_g02_is_sealed_exact_p5_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot13-candidate01-g02-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("g02_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_CANDIDATE_G02_V1", core)
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["selected_proposition_id"] == "P5" and receipt["p6_fallback_authority"] == "ABSENT"
    assert receipt["factual_authority_widening"] == "ABSENT_EXACT_P5_ONLY"
    assert receipt["qualification_result"].startswith("PASS_")
    assert receipt["modality_result"].startswith("PASS_")
    assert receipt["temporal_boundary_result"].startswith("PASS_")
    assert receipt["scope_boundary_result"].startswith("PASS_")
    assert receipt["known_unknown_boundary_result"].startswith("PASS_")
    assert receipt["creative_nonfactual_separation_result"].startswith("PASS_")
    assert receipt["sealed_mapping_accessed"] is False and receipt["mechanism_adjudication_performed"] is False
    assert receipt["candidate_bytes_unchanged"] is True
    assert receipt["eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE"
    assert all(value is False for value in receipt["authority_matrix"].values())
