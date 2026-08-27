import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / ".pastilaacida-voice-v2-bounded-initial-production-allowlist-owner-adjudication-v1-evidence"
)


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_packet_is_exactly_three_proven_tuples_and_activates_nothing():
    proposal = load("01-bounded-allowlist-proposal.json")
    assert proposal["proposed_expression_count"] == 3
    assert proposal["proposed_surface_count"] == 3
    assert {
        (e["expression_identity"], e["surface_identity"]) for e in proposal["entries"]
    } == {
        ("ro-expression-v1:65f9b0c32e8e886b8d0f", "SURFACE_BOUNDED_POOL_02_V1"),
        ("ro-expression-v1:1068794b4bf34c8914dc", "SURFACE_BOUNDED_POOL_01_V1"),
        ("ro-expression-v1:0e6562965022d3dd391f", "SURFACE_BOUNDED_POOL_03_V1"),
    }
    assert load("04-residual-gap-status.json")["production_activation"] == {
        "expressions": 0,
        "surfaces": 0,
    }


def test_packet_excludes_implicit_and_proof_authority_activation():
    boundary = load("02-scope-and-exclusions.json")
    assert boundary["proof_authority_promotion"] is False
    assert any("wildcard" in item for item in boundary["excluded"])
    assert any("SURFACE_BOUNDED_POOL_04_V1" in item for item in boundary["excluded"])
    assert boundary["model_provider_model_load_calls"] == [0, 0, 0]


def test_manifest_and_file_hashes_are_canonical_and_complete():
    manifest = load("manifest.json")
    assert manifest["owner_disposition"] is None
    assert manifest["production_activation"] == {"expressions": 0, "surfaces": 0}
    hashes = load("05-hashes.json")
    for name, identity in hashes.items():
        assert (
            identity
            == "sha256:" + hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
        )
    for path in EVIDENCE.glob("*.json"):
        raw = path.read_bytes()
        parsed = json.loads(raw)
        expected = (
            json.dumps(
                parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n"
        ).encode()
        assert raw == expected
