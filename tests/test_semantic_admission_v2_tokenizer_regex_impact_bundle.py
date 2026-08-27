import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / ".semantic-admission-v2-tokenizer-regex-impact-v1-evidence"
MANIFEST = EVIDENCE_ROOT / "manifest.json"
ASSESSMENT = EVIDENCE_ROOT / "impact-assessment.json"
UPSTREAM = (
    ROOT
    / ".semantic-admission-v2-run4-wsl-access-preflight-v1-evidence"
    / "manifest.json"
)


def test_tokenizer_regex_impact_bundle_hashes_and_identity_rederive():
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


def test_tokenizer_regex_assessment_is_bounded_and_non_authorizing():
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    assessment = json.loads(ASSESSMENT.read_text("utf-8"))
    upstream = json.loads(UPSTREAM.read_text("utf-8"))
    comparison = assessment["comparison"]

    assert assessment["source_preflight_identity"] == upstream["canonical_identity"]
    assert (
        assessment["worker_sha256"]
        == hashlib.sha256(
            (ROOT / "scripts/tokenizer_regex_impact_worker_v1.py").read_bytes()
        ).hexdigest()
    )
    assert manifest["result"] == assessment["result"] == "PASS"
    assert assessment["sample_count"] == manifest["sample_count"] == 15
    assert assessment["exact_gate_f_prompt_count"] == 10
    assert comparison["different_count"] == 0
    assert all(
        record["identical_token_ids"]
        and record["legacy_sha256"] == record["fixed_sha256"]
        for record in comparison["records"]
    )
    assert manifest["global_tokenizer_equivalence_claimed"] is False
    assert assessment["runner_modified"] is False
    assert assessment["model_load_started"] is False
    assert assessment["inference_started"] is False
    assert assessment["model_calls"] == 0
    assert assessment["provider_calls"] == 0
    assert assessment["run4_execution_authorized"] is False
    assert assessment["runtime_authority"] is False
    assert assessment["training_authority"] is False
