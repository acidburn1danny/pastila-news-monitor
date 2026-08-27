import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT / "docs/artifacts/canonical-wsl-boundary-v1-operational-acceptance-pack.json"
)


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_operational_acceptance_identity_and_bindings_rederive():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == value["canonical_identity"]
    )
    assert (
        _sha(value["deterministic_evidence"]["test_path"])
        == value["deterministic_evidence"]["test_sha256"]
    )
    assert (
        _sha(value["live_transport_evidence"]["script_path"])
        == value["live_transport_evidence"]["script_sha256"]
    )
    remediation = value["remediation_candidate"]
    assert (
        _sha(remediation["implementation_path"]) == remediation["implementation_sha256"]
    )
    assert value["frozen_authority"]["boundary_sha256_after_pack"] == _sha(
        "src/pastila_scout/wsl_execution_v1/boundary.py"
    )


def test_pack_preserves_all_authority_and_migration_stops():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    scope = value["scope"]
    assert scope["model_loaded"] is False
    assert scope["model_generation"] is False
    assert scope["prompt_or_semantic_change"] is False
    assert scope["authority_or_eligibility_change"] is False
    assert scope["grandfathered_launchers_migrated"] == 0
    assert scope["grandfathered_launchers_preserved"] == 16
    assert value["remediation_candidate"]["active_consumer_binding"] is False
    assert value["remediation_candidate"]["packaging_binding"] is False
