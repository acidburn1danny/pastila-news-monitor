import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / ".semantic-admission-v2-run4-wsl-access-preflight-v1-evidence"
MANIFEST = EVIDENCE_ROOT / "manifest.json"
PREFLIGHT = EVIDENCE_ROOT / "zero-inference-wsl-access-preflight.json"


def test_run4_preflight_bundle_hashes_and_identity_rederive():
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    artifact_hashes = []

    for artifact in manifest["artifacts"]:
        actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        assert actual == artifact["sha256"]
        artifact_hashes.append(actual)

    assert (
        hashlib.sha256("\n".join(artifact_hashes).encode()).hexdigest()
        == manifest["canonical_identity"]
    )


def test_run4_preflight_receipt_preserves_zero_inference_authority_boundary():
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    receipt = json.loads(PREFLIGHT.read_text("utf-8"))

    assert manifest["result"] == receipt["result"] == "PASS"
    assert receipt["constrained_lifecycle"]["tokenizer_load_succeeded"] is True
    assert receipt["constrained_lifecycle"]["model_load_started"] is False
    assert receipt["inference_started"] is False
    assert receipt["model_calls"] == 0
    assert receipt["provider_calls"] == 0
    assert receipt["run4_execution_authorized"] is False
    assert receipt["runtime_authority"] is False
    assert receipt["training_authority"] is False
    assert manifest["tokenizer_regex_warning_open"] is True
