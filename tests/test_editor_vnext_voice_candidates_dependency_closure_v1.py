import json
from pathlib import Path

from scripts.materialize_editor_vnext_voice_candidates_v1 import CANDIDATES, EXPECTED_FREE, PRODUCT, RELATIVE_DESTINATION, identify, restore_proof


def test_bounded_candidates_and_destination():
    assert PRODUCT == Path("/root/pastila-vnext/v1")
    assert RELATIVE_DESTINATION == Path("components/voice-candidates-v1")
    assert EXPECTED_FREE == 74_017_955_312
    assert [(item["repo_id"], item["revision"], item["expected_bytes"]) for item in CANDIDATES] == [
        ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218", 16_397_461_266),
        ("Qwen/Qwen2.5-7B-Instruct", "a09a35458c702b33eeacc393d103063234e8bc28", 15_242_807_270),
    ]
    assert [item["source_candidate_id"] for item in CANDIDATES] == ["C1_QWEN3_8B", "C2_QWEN25_7B"]


def test_identity_excludes_only_identity_field():
    value = identify({"schema": "fixture", "x": 1}, "lock_identity")
    assert value == identify(value, "lock_identity")


def test_manifest_identity_modes_are_explicit():
    manifest = json.loads(Path("docs/artifacts/editor-core-text-realizer-model-acquisition-v1-snapshots.json").read_text(encoding="utf-8"))
    assert any(item["sha256"] for model in manifest["models"] for item in model["files"])
    assert any(item["sha256"] is None for model in manifest["models"] for item in model["files"])


def test_restore_proof_rejects_persistent_or_unbounded_root():
    try:
        restore_proof(Path("C:/synthetic-source-not-read"), Path("C:/unbounded-restore-not-created"))
    except ValueError as error:
        assert "bounded temporary" in str(error)
    else:
        raise AssertionError("unbounded restore root accepted")


def test_materialized_closure_is_dependency_only_when_present():
    path = Path("docs/artifacts/editor-vnext-voice-candidates-dependency-closure-v1.json")
    if not path.exists() or path.read_text(encoding="utf-8").strip() == "{}":
        return
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["status"] == "PASS_DEPENDENCY_ONLY_NO_MODEL_LOAD"
    assert value["snapshot_bytes"] == 31_640_268_536
    assert all(value[key] is False for key in ("model_loaded", "inference_performed", "download_performed", "training_performed", "optimizer_created"))
    assert value["legacy_dependency_count"] == value["hardlinks"] == value["symlinks"] == value["legacy_path_hits"] == 0
