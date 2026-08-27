import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT / ".pastilaacida-voice-v2-signed-installer-authority-blocker-v1-evidence"
)


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_signed_installer_stops_on_both_authority_blockers():
    assert load("manifest.json")["verdict"] == "SIGNED_INSTALLER_BLOCKED"
    assert (
        load("01-signing-authority-preflight.json")["matching_certificate_count"] == 0
    )
    source = load("02-installer-source-authority-preflight.json")
    assert source["historical_wrapper_may_be_bypassed"] is False
    boundary = load("03-fail-closed-boundary.json")
    assert boundary["open_release_blocking_gaps"] == 2
    assert boundary["signed_installer_built"] is False
    assert boundary["installer_executed"] is False


def test_blocker_evidence_is_canonical_and_hash_index_matches():
    for name, identity in load("05-hashes.json").items():
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
