"""Verify Pilot 10 V5.2 proposition-sufficiency receipt boundaries."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot10_sufficiency_receipt_is_sealed_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot10-proposition-sufficiency-receipt-v5-2.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-proposition-sufficiency-audit-v5-2.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("receipt_identity")
    assert identity == seal("B2_PILOT10_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5_2", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_PILOT10_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5_2", core)
    assert receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT"
    assert receipt["selected_proposition_id"] == "P3"
    assert len(receipt["all_proposition_assessments"]) == 7
    assert receipt["source_relation_sufficiency"]["candidate_surface"] is None
    assert receipt["source_relation_sufficiency"]["realization_plan"] is None
    assert receipt["source_relation_sufficiency"]["witness_plan"] is None
    assert receipt["mechanism_label_exposed"] is False
    assert receipt["assignment_performed"] is False
    assert receipt["creative_premise_family_id"] == "UNASSIGNED"
    assert receipt["constructor_v5_2_compatibility_evaluated"] is False
    assert receipt["realization_or_witness_planning_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["verdict"] == "PASS_SOURCE_ONLY_NO_ASSIGNMENT_NO_PLANNING_ZERO_CONSTRUCTION"
