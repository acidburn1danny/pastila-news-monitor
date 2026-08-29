from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / (
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
    "case01-successor-issuance-packet-v1-2-1-generation-telemetry-bound")
RECEIPT = "6d86f71011bb56d9d2a462a1394a5449a71cd2c7bcd22a097b2a057f7e677868"


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def test_generation_telemetry_receipt_is_exact_issued_and_unconsumed():
    candidate = json.loads((PACKET / "authority-receipt-candidate.json").read_bytes())
    manifest = json.loads((PACKET / "manifest.json").read_bytes())
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = RECEIPT
    assert candidate["proposed_receipt_identity"] == RECEIPT
    assert (PACKET / "authority-receipt-issued.json").read_bytes() == _canonical(issued)
    assert manifest["attempts"] == {"completed": 0, "ceiling": 1}
    assert all(value is False for value in manifest["execution"].values())
    assert not Path(manifest["proposed_evidence_root"]).exists()


def test_issuance_verification_has_no_execution_surface():
    source = Path(__file__).read_text("utf-8")
    forbidden = (".exe" + "cute(", "wsl" + ".exe", "from_" + "pretrained",
                 ".gene" + "rate(", "nvidia" + "-smi")
    assert all(term not in source for term in forbidden)
