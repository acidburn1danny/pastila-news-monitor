from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "docs/artifacts/humor-mechanics-curriculum-v1.manifest.json"
def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_identity(value: dict[str, object], identity_key: str) -> str:
    body = dict(value)
    body.pop(identity_key)
    canonical = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_frozen_curriculum_has_exactly_five_complete_batches() -> None:
    manifest = _load(CURRICULUM)
    mechanisms = manifest["mechanisms"]

    assert manifest["lifecycle"] == "OWNER_APPROVED_AND_FROZEN"
    assert manifest["mechanism_count"] == len(mechanisms) == 50
    assert len({item["id"] for item in mechanisms}) == 50
    assert sorted(item["ordinal"] for item in mechanisms) == list(range(1, 51))
    assert Counter(item["batch"] for item in mechanisms) == Counter(
        {1: 10, 2: 10, 3: 10, 4: 10, 5: 10}
    )
    assert _canonical_identity(manifest, "canonical_identity") == manifest[
        "canonical_identity"
    ]


def test_curriculum_grants_no_runtime_training_or_integration_authority() -> None:
    manifest = _load(CURRICULUM)

    assert manifest["authority"]["runtime_authority"] == "none"
    assert manifest["authority"]["training_authority"] == "none"
    assert "CORE_OR_VOICE_INTEGRATION" in manifest["non_goals"]
    assert "RUNTIME_BEHAVIOR_CHANGE" in manifest["non_goals"]
    assert "TRAINING" in manifest["non_goals"]
    assert manifest["level_2_composition_evidence"]["production_routing_authorized"] is False


def test_evidence_audit_specification_is_exactly_bound() -> None:
    manifest = _load(CURRICULUM)
    specification = ROOT / manifest["evidence_audit_specification"]["path"]

    assert hashlib.sha256(specification.read_bytes()).hexdigest() == manifest[
        "evidence_audit_specification"
    ]["sha256"]
