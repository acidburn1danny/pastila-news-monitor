import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-phase2-token-projector-v1-freeze.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_owner_freeze_identity_and_candidate_bytes_are_reproducible():
    freeze = _load(FREEZE)
    fields = freeze["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == freeze["canonical_identity"]
    candidate = freeze["frozen_candidate"]
    candidate_path = ROOT / candidate["path"]
    assert hashlib.sha256(candidate_path.read_bytes()).hexdigest() == candidate["sha256"]
    assert _load(candidate_path)["canonical_identity"] == candidate["canonical_identity"]


def test_freeze_preserves_candidate_only_authority_boundary():
    freeze = _load(FREEZE)
    assert freeze["owner_disposition"] == "APPROVED_AND_FROZEN"
    assert freeze["status"] == "FROZEN"
    assert not any(freeze["authority"].values())
    assert not any(freeze["preservation"].values())
