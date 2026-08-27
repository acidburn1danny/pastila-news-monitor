import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/canonical-wsl-boundary-v1-1-post-sleep-closure.json"


def test_post_sleep_closure_identity_and_receipt_rederive():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == value["canonical_identity"]
    )
    execution = value["single_execution"]
    assert execution["attempt_count"] == 1
    assert execution["retry_count"] == 0
    assert execution["return_code"] == 0
    assert execution["failure_code"] is None
    assert execution["stdout"] == "PASTILA_INSTALLED_WSL_V1_1_OK"
    assert execution["model_loads"] == execution["inference_calls"] == 0
    assert value["overall_disposition"] == "PASS_COMPLETE"


def test_post_sleep_closure_preserves_migration_and_authority_boundaries():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["resume_evidence"]["postdates_v1_1_installation"] is True
    assert value["resume_evidence"]["predates_transport_execution"] is True
    assert value["governance"]["grandfathered_launchers_migrated"] == 0
    assert value["governance"]["grandfathered_launchers_preserved"] == 16
    assert (
        value["governance"]["prompt_model_semantic_or_eligibility_authority_changed"]
        is False
    )
