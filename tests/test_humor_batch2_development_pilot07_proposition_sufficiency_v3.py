import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_proposition_sufficiency_receipt_is_sealed_and_non_authorizing():
    receipt = json.loads((ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-proposition-sufficiency-receipt-v3.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-proposition-sufficiency-audit-v3.json").read_text(encoding="utf-8"))
    receipt_core = dict(receipt)
    receipt_identity = receipt_core.pop("receipt_identity")
    assert receipt_identity == seal("B2_PILOT07_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V3", receipt_core)
    audit_core = dict(audit)
    audit_identity = audit_core.pop("audit_identity")
    assert audit_identity == seal("B2_PILOT07_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V3", audit_core)
    assert receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT"
    assert receipt["selected_proposition_id"] == "P5"
    assert len(receipt["all_proposition_assessments"]) == 6
    assert receipt["abstract_adjacent_link_witness"]["candidate_surface"] is None
    assert receipt["mechanism_label_exposed"] is False
    assert receipt["creative_premise_family_id"] == "UNASSIGNED"
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["verdict"] == "PASS_SOURCE_ONLY_NO_ASSIGNMENT_ZERO_CONSTRUCTION"
