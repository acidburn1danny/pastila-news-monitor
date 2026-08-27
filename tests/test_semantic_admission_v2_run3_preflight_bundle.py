import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT / ".semantic-admission-v2-run3-constrained-preflight-v1-evidence/manifest.json"
)


def test_run3_preflight_bundle_hashes_and_identity_rederive():
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    hashes = [artifact["sha256"] for artifact in manifest["artifacts"]]

    for artifact in manifest["artifacts"]:
        if (
            artifact["path"]
            == "tests/test_semantic_admission_v2_run3_constrained_plan.py"
        ):
            # The pre-execution test evolves in the successor commit once the
            # sealed execution evidence exists. Its predecessor blob remains
            # preserved by the preflight commit and recorded hash.
            assert artifact["sha256"] == (
                "fe1e97f784166128c2550d43a0542a9b1b870ff3a733342d26abebe08b9db363"
            )
            continue
        actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        assert actual == artifact["sha256"]

    assert (
        hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        == manifest["canonical_identity"]
    )
    assert manifest["provider_calls_performed"] == 0
    assert manifest["model_calls_performed"] == 0
    assert manifest["run3_authorized"] is False
    assert manifest["runtime_authority"] is False
