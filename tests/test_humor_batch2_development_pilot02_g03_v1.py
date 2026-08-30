from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def _load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def _seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_g03_reconciliation_preserves_independent_blind_results() -> None:
    value = _load(
        "humor-mechanics-batch2-development-pilot02-candidate01-g03-reconciliation-v1.json"
    )
    identity = value.pop("reconciliation_identity")

    assert identity == _seal("B2_DEVELOPMENT_PILOT02_G03_RECONCILIATION_V1", value)
    assert value["blind_pass_commit"] == "0af2097ccdf0aa03dc0a9f6dcb3f58a67d7649f5"
    assert value["mapping_revealed_after_blind_freeze"] is True
    assert value["open_pass"]["pass_identity"] == (
        "13c18428dc201f2ca936cf264832a8e039cf7a99513efdc91bb8246a1113338a"
    )
    assert value["open_pass"]["verbatim_primary"] == "paradox temporal autoanulant"
    assert value["open_pass"]["verbatim_supporting"] == [
        "cauzalitate circulară",
        "escaladare logică absurdă",
        "literalizarea unei condiții procedurale",
    ]
    assert value["open_pass"]["posthoc_label_rewrite"] is False
    assert value["contrast_pass"]["pass_identity"] == (
        "5980b6fa8d9a86b64204c113f9bb0c2114958155b3f5207801a12e4f101be14b"
    )
    assert value["contrast_pass"]["primary_choice"] == "Absurd Logical Extension"
    assert value["contrast_pass"]["primary_role"] == "DOMINANT"
    assert value["substantive_disagreement"] is False
    assert value["classification"] == "TARGET_RECOVERED_DOMINANT"


def test_g03_receipt_is_sealed_and_grants_no_downstream_authority() -> None:
    value = _load(
        "humor-mechanics-batch2-development-pilot02-candidate01-g03-receipt-v1.json"
    )
    identity = value.pop("g03_receipt_identity")

    assert identity == _seal("B2_DEVELOPMENT_PILOT02_G03_RECEIPT_V1", value)
    assert value["g03_validity_status"] == "VALID_BLIND_REVIEW"
    assert value["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT"
    assert value["target_dominant_recovery_established"] is True
    assert value["candidate_modified"] is False
    assert value["g03b_performed"] is False
    assert value["g03c_performed"] is False
    assert not any(value["authority_matrix"].values())
