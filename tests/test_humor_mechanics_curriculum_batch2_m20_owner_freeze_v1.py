from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "docs/artifacts/humor-mechanics-curriculum-v1-batch2-m20-owner-freeze-v1.json"
)


def test_m20_owner_freeze_is_source_bound_and_non_executing() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["status"] == "OWNER_FROZEN"
    assert receipt["source"]["source_sha256"] == (
        "c0ed747474bdc9a4c0a4024eddee56415b36e40ba937f592983072d64699c276"
    )
    assert receipt["source"]["byte_exact"] is True
    assert receipt["source"]["edited"] is False
    assert receipt["source"]["normalized"] is False
    assert all(value is False for value in receipt["authority"].values())


def test_m20_owner_freeze_preserves_exact_roles_and_gate_results() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    gates = receipt["gates"]
    annotations = gates["B2-G03-MECHANISM_AND_CONTRAST"]["annotations"]

    assert gates["B2-G02-FACTUAL_AND_TARGET_BOUNDARY"]["compatibility"] == (
        "COMPATIBLE_ONLY_AS_NONFACTUAL_EXCERPT"
    )
    assert [(item["mechanism_id"], item["role"]) for item in annotations] == [
        ("HMCV1-B01-M05-FRAME_TRANSFER", "DOMINANT"),
        ("HMCV1-B02-M10-ROLE_SIMULATION", "SUPPORTING"),
        ("HMCV1-B01-M08-ESCALATION", "COMPOSITION"),
    ]
    assert gates["B2-G04-ROMANIAN_NATURALNESS"]["state"] == (
        "REVIEWER_ACCEPTED_NATURAL"
    )
    assert gates["B2-G05-OWNER_FREEZE"]["decision"] == (
        "APPROVE M20 OWNER_FROZEN"
    )


def test_m20_owner_freeze_canonical_identity() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    claimed = receipt.pop("canonical_identity")
    canonical = json.dumps(
        receipt,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert hashlib.sha256(canonical).hexdigest() == claimed
