import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/canonical-wsl-boundary-v1-1-operational-freeze.json"
POST_SLEEP_CLOSURE = (
    ROOT / "docs/artifacts/canonical-wsl-boundary-v1-1-post-sleep-closure.json"
)
CORE_REBINDING = ROOT / "docs/artifacts/canonical-wsl-boundary-v1-1-core-rebinding.json"


def test_operational_freeze_identity_and_boundaries_rederive():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    post_sleep_closure = json.loads(POST_SLEEP_CLOSURE.read_text("utf-8"))
    core_rebinding = json.loads(CORE_REBINDING.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == value["canonical_identity"]
    )
    assert value["status"] == "FROZEN"
    assert value["owner_disposition"] == "APPROVED_AND_FROZEN"
    assert (
        value["frozen_post_sleep_closure_identity"]
        == post_sleep_closure["canonical_identity"]
    )
    assert (
        value["frozen_core_rebinding_identity"] == core_rebinding["canonical_identity"]
    )
    assert value["operational_acceptance"]["model_loads"] == 0
    assert value["operational_acceptance"]["inference_calls"] == 0
    assert value["preservation"]["grandfathered_frozen_evaluation_launchers"] == 16
    assert value["preservation"]["grandfathered_launchers_migrated"] == 0
    assert value["authority"]["additional_probe_migration_authorized"] is False
