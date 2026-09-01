from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot08_attempt_is_consumed_once_and_collision_gate_is_pending():
    base = ROOT / "docs/artifacts"
    candidate = (base / "humor-mechanics-batch2-development-pilot08-candidate01-v1.txt").read_bytes()
    evidence = json.loads((base / "humor-mechanics-batch2-development-pilot08-construction-attempt01-v1.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(candidate).hexdigest() == evidence["candidate_surface_sha256"] == "bc71da32026e9173440a494279fd4dca752cfc8c5547abcaa1ad922bdda0368a"
    assert evidence["candidate_identity"] == "6f2aca6eafc4773576a00001d83d1a0e5c2bf5a2c53d1ae2930c2f3147457fb8"
    assert evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}
    assert evidence["capability"]["consumed"] is True and evidence["capability"]["reads"] == 1
    assert evidence["terminal_classification"] == "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
    assert evidence["fragment_collision_evaluation"] == "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02"
    assert evidence["g02_eligibility"] is False
    assert evidence["post_construction_g02b_verdict"] == "PASS"
    assert evidence["retry_authority"] is evidence["repair_authority"] is evidence["selection_authority"] is False
    assert not any(evidence["authority_matrix"].values())
    core = dict(evidence); identity = core.pop("evidence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT08_CONSTRUCTION_ATTEMPT01_V1", core)
