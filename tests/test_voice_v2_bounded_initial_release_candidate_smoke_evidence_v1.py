import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT / ".pastilaacida-voice-v2-bounded-initial-release-candidate-smoke-v1-evidence"
)


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_corrected_portable_rc_passes_but_signed_installer_remains_blocked():
    manifest = load("manifest.json")
    assert manifest["production_activation"] == {"expressions": 3, "surfaces": 3}
    assert manifest["open_production_binding_gaps"] == 0
    assert manifest["open_release_packaging_gaps"] == 1
    assert (
        manifest["verdict"]
        == "PORTABLE_RC_SMOKE_PASSED_SIGNED_INSTALLER_NOT_AUTHORIZED"
    )
    assert load("03-installed-smoke-results.json")[
        "model_provider_model_load_calls"
    ] == [0, 0, 0]
    boundary = load("04-release-boundary.json")
    assert boundary["guardrail_weakened_or_bypassed"] is False
    assert boundary["signed_inno_installer_built"] is False


def test_rc_evidence_is_canonical_and_hash_index_matches():
    for name, identity in load("06-hashes.json").items():
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
