import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_corrected_p5_witness_is_consistent_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot07-proposition-sufficiency-receipt-v3-1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot07-proposition-sufficiency-remediation-audit-v3-1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("receipt_identity")
    assert identity == seal("B2_PILOT07_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V3_1", core)
    links = receipt["abstract_adjacent_link_witness"]["adjacent_links"]
    assert links == ["ISSUE_OBSERVATION_IS_THE_EXPLICIT_CONDITION_FOR_REPORT_ENTRY", "REPORT_ENTRY_IS_EXPLICITLY_DIRECTED_TO_LATER_ANALYSIS"]
    selected = [item for item in receipt["all_proposition_assessments"] if item["selection_status"] == "SELECTED_SUFFICIENT"]
    assert len(selected) == 1 and selected[0]["proposition_id"] == "P5"
    assert selected[0]["abstract_adjacent_link_witness"]["adjacent_links"] == links
    assert receipt["candidate_surface"] is None and not any(receipt["authority_matrix"].values())
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_PILOT07_POST_G01_PROPOSITION_SUFFICIENCY_REMEDIATION_AUDIT_V3_1", core)
    assert audit["deterministic_blockers"] == []
