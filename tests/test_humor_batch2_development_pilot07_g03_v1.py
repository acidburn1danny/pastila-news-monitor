import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_g03_recovers_the_sealed_target_dominantly():
    base = ROOT / "docs/artifacts"
    reconciliation = json.loads(
        (base / "humor-mechanics-batch2-development-pilot07-g03-reconciliation-v1.json").read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (base / "humor-mechanics-batch2-development-pilot07-g03-receipt-v1.json").read_text(encoding="utf-8")
    )

    reconciliation_core = dict(reconciliation)
    reconciliation_identity = reconciliation_core.pop("reconciliation_identity")
    assert reconciliation_identity == seal("B2_DEVELOPMENT_PILOT07_G03_RECONCILIATION_V1", reconciliation_core)

    receipt_core = dict(receipt)
    receipt_identity = receipt_core.pop("g03_receipt_identity")
    assert receipt_identity == seal("B2_DEVELOPMENT_PILOT07_G03_RECEIPT_V1", receipt_core)

    assert receipt["g03_validity_status"] == "VALID_BLIND_REVIEW"
    assert receipt["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT"
    assert reconciliation["mapping_revealed_after_both_passes_frozen"] is True
    assert reconciliation["target_dominant_recovery_established"] is True
    assert reconciliation["substantive_disagreement"] is False
    assert receipt["open_recovery"]["role"] == "DOMINANT"
    assert receipt["open_recovery"]["confidence"] == "HIGH"
    assert receipt["contrast_recovery"] == {
        "confidence": "HIGH",
        "primary": "ABSURD_LOGICAL_EXTENSION",
        "role": "DOMINANT",
        "supporting": [],
    }
    assert receipt["g03b_performed"] is False and receipt["g03c_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
