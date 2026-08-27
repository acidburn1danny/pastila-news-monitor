import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT / ".pastilaacida-voice-v2-bounded-initial-production-activation-v1-evidence"
)


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_activation_closes_final_gap_without_calls_or_implicit_authority():
    manifest = load("manifest.json")
    assert manifest["production_activation"] == {"expressions": 3, "surfaces": 3}
    assert manifest["open_blocking_gaps"] == 0
    assert manifest["verdict"] == "READY_FOR_BOUNDED_PRODUCTION_ACTIVATION"
    assert load("04-zero-call-verification.json")["model_calls"] == 0
    enforcement = load("03-fail-closed-enforcement.json")
    assert enforcement["proof_authority_promoted"] is False
    assert enforcement["wildcard_family_or_pool_activation"] is False


def test_evidence_is_canonical_and_hash_index_matches():
    for name, identity in load("07-hashes.json").items():
        assert (
            identity
            == "sha256:" + hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
        )
    for path in EVIDENCE.glob("*.json"):
        raw = path.read_bytes()
        expected = (
            json.dumps(
                json.loads(raw),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
        assert raw == expected
