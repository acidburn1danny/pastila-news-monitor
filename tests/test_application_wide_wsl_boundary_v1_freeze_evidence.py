import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = (
    ROOT
    / "docs"
    / "artifacts"
    / "application-wide-canonical-wsl-execution-boundary-v1-freeze.json"
)
CANDIDATE = (
    ROOT
    / "docs"
    / "artifacts"
    / "application-wide-canonical-wsl-execution-boundary-v1.json"
)


def test_freeze_identity_and_candidate_binding_rederive():
    freeze = json.loads(FREEZE.read_text("utf-8"))
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    fields = freeze["identity_derivation"]["ordered_fields"]

    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == freeze["canonical_identity"]
    )
    assert freeze["frozen_candidate_identity"] == candidate["canonical_identity"]
    assert freeze["owner_disposition"] == "APPROVED_AND_FROZEN"
    assert freeze["status"] == "FROZEN"


def test_freeze_preserves_transport_and_authority_boundaries():
    freeze = json.loads(FREEZE.read_text("utf-8"))
    preservation = freeze["preservation"]
    authority = freeze["authority"]

    assert preservation["transport_only"] is True
    assert preservation["grandfathered_frozen_evaluation_launchers"] == 16
    assert preservation["historical_artifacts_rewritten"] is False
    assert authority["boundary_semantic_authority"] is False
    assert authority["boundary_model_or_prompt_authority"] is False
    assert authority["evaluator_runner_rebinding"] is False
    assert authority["additional_probe_migration"] is False
    assert authority["runtime_expansion_beyond_approved_consumers"] is False
