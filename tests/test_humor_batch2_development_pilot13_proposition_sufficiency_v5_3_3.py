import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot13_sufficiency_receipt_is_sealed_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot13-proposition-sufficiency-receipt-v5-3-3.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-proposition-sufficiency-audit-v5-3-3.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("receipt_identity")
    assert identity == seal("B2_PILOT13_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5_3_3", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_PILOT13_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5_3_3", core)
    assert receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT"
    assert receipt["selected_proposition_id"] == "P5"
    assert receipt["eligible_propositions"] == ["P5", "P6"]
    assert receipt["selection_rule"] == "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS"
    assert len(receipt["all_proposition_assessments"]) == 8
    relation = receipt["source_relation_sufficiency"]
    assert relation["candidate_surface"] is relation["mechanism"] is relation["assignment"] is None
    assert relation["constructor_compatibility"] is relation["semantic_role_plan"] is relation["affordance_plan"] is None
    assert relation["realization_plan"] is relation["witness_plan"] is relation["morphological_alignment_plan"] is None
    assert receipt["downstream_suitability_considered"] is False
    assert receipt["mechanism_label_exposed"] is False and receipt["assignment_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["exact_selected_supporting_span_binding"] == "PASS"
    assert audit["deterministic_blockers"] == []
