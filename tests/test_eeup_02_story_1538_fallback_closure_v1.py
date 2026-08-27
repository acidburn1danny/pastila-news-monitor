import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / ".pastilaacida-voice-v2-eeup-02-story-1538-fallback-proof-owner-closure-v1-evidence"
)


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_owner_accepted_exact_fallback_proof():
    closure = load("01-owner-accepted-proof-closure.json")
    assert (
        closure["closure_status"]
        == "EEUP_02_ALTERNATE_FALLBACK_PROOF_ACCEPTED_AND_CLOSED"
    )
    assert closure["accepted_properties"]["genuine_prefilter_pool_count"] == 2
    assert closure["accepted_properties"]["governed_fallback_pool_count"] == 1


def test_both_known_blockers_are_resolved_pending_final_audit():
    residual = load("02-residual-gap-transition.json")
    assert residual["open_blocking_gaps"] == 0
    assert all(item["status"].startswith("RESOLVED") for item in residual["gaps"])
    assert residual["readiness"] == "PENDING_FINAL_RESIDUAL_GAP_AUDIT"


def test_activation_and_calls_remain_zero():
    manifest = load("manifest.json")
    assert manifest["production_activation"] == {"expressions": 0, "surfaces": 0}
    assert manifest["model_provider_model_load_calls"] == [0, 0, 0]
