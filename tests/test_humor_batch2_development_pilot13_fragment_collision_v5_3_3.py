import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_collision_gate_is_sealed_zero_hit_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot13-fragment-collision-receipt-v5-3-3.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-fragment-collision-audit-v5-3-3.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_POSTCONSTRUCTION_FRAGMENT_COLLISION_RECEIPT_V5_3_3", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_POSTCONSTRUCTION_FRAGMENT_COLLISION_AUDIT_V5_3_3", core)
    assert receipt["verdict"] == "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION"
    assert receipt["collision_count"] == len(receipt["exact_or_normalized_collisions"]) == 0
    assert receipt["denyset_hash_count"] == 2698 and receipt["total_candidate_windows_tested"] == 399
    assert receipt["blind_reserve_accessed"] is False and receipt["candidate_bytes_unchanged"] is True
    assert receipt["capability_state"] == "CONSUMED_1_OF_1"
    assert receipt["g02_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW"
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["g02_review_performed"] is False and audit["constructor_provider_emitter_invocations_added"] == "0/0/0"
