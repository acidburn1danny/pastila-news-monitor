import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_attempt_is_consumed_once_and_evidence_is_sealed():
    base = ROOT / "docs/artifacts"
    candidate = (base / "humor-mechanics-batch2-development-pilot07-candidate01-v1.txt").read_bytes()
    evidence = json.loads((base / "humor-mechanics-batch2-development-pilot07-construction-attempt01-v1.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(candidate).hexdigest() == evidence["candidate_surface_sha256"] == "769228fc99006e0f665360f28805f31d4480419095de1f1fba5794319cc1bfa8"
    assert evidence["candidate_identity"] == "44c76c090e226d0ef947e2fc07307fb862761e94950c4eb378b8b3d258427bc1"
    assert evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}
    assert evidence["capability"]["consumed"] is True and evidence["capability"]["reads"] == 1
    assert evidence["selected_proposition_id"] == "P5"
    assert evidence["post_construction_g02b_verdict"] == "PASS"
    assert evidence["terminal_classification"] == "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY"
    assert evidence["retry_authority"] is evidence["repair_authority"] is evidence["selection_authority"] is False
    assert not any(evidence["authority_matrix"].values())
    core = dict(evidence); identity = core.pop("evidence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CONSTRUCTION_ATTEMPT01_V1", core)
