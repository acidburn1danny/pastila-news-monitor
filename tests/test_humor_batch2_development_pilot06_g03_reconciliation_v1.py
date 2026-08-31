import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot06_g03_preserves_blind_disagreement():
    base = ROOT / "docs/artifacts"
    reconciliation = json.loads((base / "humor-mechanics-batch2-development-pilot06-g03-reconciliation-v1.json").read_text(encoding="utf-8"))
    receipt = json.loads((base / "humor-mechanics-batch2-development-pilot06-g03-receipt-v1.json").read_text(encoding="utf-8"))
    core = dict(reconciliation); identity = core.pop("reconciliation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT06_G03_RECONCILIATION_V1", core)
    receipt_core = dict(receipt); receipt_identity = receipt_core.pop("g03_receipt_identity")
    assert receipt_identity == seal("B2_DEVELOPMENT_PILOT06_G03_RECEIPT_V1", receipt_core)
    assert receipt["g03_validity"] == "VALID_BLIND_REVIEW"
    assert receipt["reconciliation_classification"] == "AMBIGUOUS_MECHANISM"
    assert reconciliation["target_dominant_recovery_established"] is False
    assert reconciliation["dominance_disagreement"]["substantive"] is True
    assert receipt["g03b_performed"] is False and receipt["g03c_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
