import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/canonical-wsl-boundary-v1-1-core-rebinding.json"


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_rebinding_identity_and_current_source_bindings_rederive():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]
    binding = value["binding"]
    assert _sha("src/pastila_scout/wsl_execution_v1_1/boundary.py") == binding["boundary_v1_1_sha256"]
    assert _sha("src/pastila_scout/experimental_core_v1_1.py") == binding["core_v1_1_sha256"]
    assert _sha("src/pastila_scout/experimental_core_v1_2.py") == binding["core_v1_2_sha256"]
    assert _sha("packaging/pyinstaller/PastilaScout.spec") == value["packaging"]["spec_sha256"]


def test_rebinding_preserves_authority_and_reports_sleep_evidence_honestly():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["binding"]["command_bytes_equivalent_to_v1"] is True
    assert value["binding"]["profile_model_prompt_and_request_contracts_changed"] is False
    assert value["governance"]["grandfathered_launchers_migrated"] == 0
    assert value["governance"]["grandfathered_launchers_preserved"] == 16
    assert value["installed_transport_smoke"]["inference_calls"] == 0
    assert value["post_sleep_observation"]["status"] == "PENDING_GENUINE_POST_INSTALL_RESUME"
