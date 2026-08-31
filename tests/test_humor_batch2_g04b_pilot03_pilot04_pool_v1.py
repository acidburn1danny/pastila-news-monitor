from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def test_g04b_fails_closed_on_shared_obligation_and_realization_shape() -> None:
    audit = json.loads((ART / "humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-v1.json").read_text(encoding="utf-8"))
    identity = audit.pop("g04b_pool_audit_identity")
    assert identity == seal("B2_G04B_PILOT03_PILOT04_POOL_AUDIT_V1", audit)
    assert audit["family_source_topic_entity_payoff_diversity"]["verdict"] == "PASS"
    assert audit["structural_realization_diversity"]["verdict"] == "FAIL_INSUFFICIENT_DIVERSITY"
    assert audit["positive_contrast_difficulty"]["verdict"] == "FAIL_INSUFFICIENT_CROSS_FAMILY_CONTRAST"
    assert audit["no_nonsemantic_label_predictability"]["verdict"] == "FAIL_NOT_ESTABLISHED"
    assert audit["g04b_verdict"] == "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION"
    assert audit["certification_granted"] is False and audit["candidate_bytes_modified"] is False
    assert not any(audit["authority_matrix"].values())


def test_g04b_receipt_is_sealed_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-receipt-v1.json").read_text(encoding="utf-8"))
    identity = receipt.pop("g04b_receipt_identity")
    assert identity == seal("B2_G04B_PILOT03_PILOT04_POOL_AUDIT_RECEIPT_V1", receipt)
    assert receipt["g04b_verdict"] == "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION"
    assert receipt["certification_granted"] is False
    assert receipt["contamination_verdict"] == "PASS_CLEAN_BOUNDED_DEVELOPMENT_POOL"
    assert receipt["next_action_requires_separate_authority"] is True
    assert not any(receipt["authority_matrix"].values())
