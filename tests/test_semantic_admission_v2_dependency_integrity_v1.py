from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.dependency_integrity_v1 import (
    DependencyIntegrityError,
    verify_and_construct,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/fixtures/semantic_admission_v2/dependency_integrity/manifest.json"
FROZEN_MANIFEST = ROOT / "docs/artifacts/semantic-admission-v2-dependency-integrity-v1.json"


def _write_manifest(path: Path, value: dict) -> None:
    identity_input = {key: item for key, item in value.items() if key != "canonical_identity"}
    value["canonical_identity"] = hashlib.sha256(
        json.dumps(identity_input, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    path.write_text(json.dumps(value), encoding="utf-8")


def test_frozen_manifest_verifies_and_constructs_two_payloads_without_executor(tmp_path: Path) -> None:
    checked = verify_and_construct(ROOT, MANIFEST, output_targets=[ROOT / ".dependency-integrity-future-output"])
    assert checked.manifest_identity == "df1948a16b37955eae869f7758d47b2d492b0917a4f3d4a69b33bdfa98c47984"
    assert [item["gate_id"] for item in checked.payloads] == ["FACTUAL_SEMANTIC", "STORY_SPECIFICITY"]
    assert "controls" not in checked.payloads[0]
    assert len(checked.payloads[1]["controls"]) == 2
    assert checked.receipt["executor_constructed"] is False
    assert checked.receipt["model_calls"] == checked.receipt["provider_calls"] == 0
    assert checked.receipt["inference_authority_issued"] is False


def test_operational_manifest_identity_remains_frozen_without_loading_raw_evidence() -> None:
    value = json.loads(FROZEN_MANIFEST.read_bytes())
    identity_input = {key: item for key, item in value.items() if key != "canonical_identity"}
    reproduced = hashlib.sha256(
        json.dumps(identity_input, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    assert reproduced == value["canonical_identity"] == "ecb6ec1ff6eabdfb0c53e849206093abf9430817dbdc57cca70bc133bca4e32d"


def test_wrong_raw_results_alias_fails_closed_before_payload_construction(tmp_path: Path) -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    next(item for item in value["dependencies"] if item["id"] == "raw_run_results")["path"] = "missing/raw-results.json"
    path = tmp_path / "manifest.json"
    _write_manifest(path, value)
    with pytest.raises(DependencyIntegrityError, match="DEPENDENCY_MISSING:.*raw-results.json"):
        verify_and_construct(ROOT, path)


def test_hash_drift_fails_closed(tmp_path: Path) -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    value["dependencies"][0]["sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    _write_manifest(path, value)
    with pytest.raises(DependencyIntegrityError, match="DEPENDENCY_HASH_MISMATCH"):
        verify_and_construct(ROOT, path)


def test_required_schema_key_failure_is_distinct(tmp_path: Path) -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    next(item for item in value["dependencies"] if item["id"] == "probe_pack")["required_keys"].append("absent_key")
    path = tmp_path / "manifest.json"
    _write_manifest(path, value)
    with pytest.raises(DependencyIntegrityError, match="DEPENDENCY_REQUIRED_KEYS_MISSING"):
        verify_and_construct(ROOT, path)


def test_existing_output_target_blocks_preflight(tmp_path: Path) -> None:
    target = ROOT / ".dependency-integrity-test-existing-output"
    target.write_text("occupied", encoding="utf-8")
    try:
        with pytest.raises(DependencyIntegrityError, match="OUTPUT_TARGET_NOT_EMPTY"):
            verify_and_construct(ROOT, MANIFEST, output_targets=[target])
    finally:
        target.unlink()
