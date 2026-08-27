import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT / ".semantic-admission-v2-run3-constrained-preflight-v1-evidence/manifest.json"
)


def test_run3_preflight_bundle_hashes_and_identity_rederive():
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    hashes = []

    for artifact in manifest["artifacts"]:
        actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        assert actual == artifact["sha256"]
        hashes.append(actual)

    assert (
        hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        == manifest["canonical_identity"]
    )
    assert manifest["provider_calls_performed"] == 0
    assert manifest["model_calls_performed"] == 0
    assert manifest["run3_authorized"] is False
    assert manifest["runtime_authority"] is False
