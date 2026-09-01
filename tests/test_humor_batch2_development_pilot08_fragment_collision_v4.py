from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot08_fragment_collision_gate_passes_without_downstream_authority():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot08-fragment-collision-receipt-v4.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot08-fragment-collision-audit-v4.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT08_POSTCONSTRUCTION_FRAGMENT_COLLISION_RECEIPT_V4", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT08_POSTCONSTRUCTION_FRAGMENT_COLLISION_AUDIT_V4", core)
    assert receipt["verdict"] == "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION"
    assert receipt["collision_count"] == 0 and receipt["exact_or_normalized_collisions"] == []
    assert receipt["blind_reserve_accessed"] is False
    assert receipt["candidate_bytes_unchanged"] is True
    assert receipt["g02_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW"
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["g02_review_performed"] is False
