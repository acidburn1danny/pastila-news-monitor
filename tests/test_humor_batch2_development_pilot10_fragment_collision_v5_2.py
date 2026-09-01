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


def test_pilot10_collision_gate_is_sealed_without_downstream_authority():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot10-fragment-collision-receipt-v5-2.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-fragment-collision-audit-v5-2.json").read_text(encoding="utf-8"))
    core = dict(receipt)
    identity = core.pop("receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_POSTCONSTRUCTION_FRAGMENT_COLLISION_RECEIPT_V5_2", core)
    core = dict(audit)
    identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_POSTCONSTRUCTION_FRAGMENT_COLLISION_AUDIT_V5_2", core)
    assert receipt["collision_count"] == len(receipt["exact_or_normalized_collisions"])
    assert receipt["blind_reserve_accessed"] is False
    assert receipt["candidate_bytes_unchanged"] is True
    assert receipt["denyset_hash_count"] == 2135
    assert all(value is False for value in receipt["authority_matrix"].values())
    assert audit["g02_review_performed"] is False
    assert audit["constructor_provider_emitter_invocations_added"] == "0/0/0"
