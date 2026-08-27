from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT / "docs/artifacts/semantic-admission-v2-wsl-dependency-boundary-repair-v1.json"
)
EVIDENCE = (
    ROOT
    / ".semantic-admission-v2-wsl-dependency-boundary-repair-v1-evidence/preflight.json"
)


def test_repair_identity_and_initializer_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    init_sha = hashlib.sha256(
        (ROOT / "src/pastila_scout/semantic_admission_v2/__init__.py").read_bytes()
    ).hexdigest()
    assert value["repair"]["initializer_sha256"] == init_sha
    parts = [
        value["artifact_id"],
        init_sha,
        "LAZY_PUBLIC_API",
        "PYDANTIC_HOST_ONLY",
        "WSL_LIGHTWEIGHT_IMPORT_PASS",
        "NO_MODEL",
        "NO_RUNTIME_CHANGE",
    ]
    assert (
        value["repair_identity"]
        == hashlib.sha256("\n".join(parts).encode()).hexdigest()
    )


def test_repair_evidence_proves_dependency_boundary_without_installing_pydantic():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["repair_identity"] == value["repair_identity"]
    assert evidence["result"] == "PASS"
    assert evidence["clean_host_import"]["pydantic_loaded"] is False
    assert evidence["wsl_import_audit"]["pydantic_available"] is False
    assert evidence["wsl_import_audit"]["pydantic_loaded"] is False
    assert "No WSL package installation" in value["non_changes"]
    for key in (
        "tokenizer_loads",
        "model_loads",
        "provider_calls",
        "inference_calls",
        "stage_c_calls",
    ):
        assert evidence[key] == 0
    assert evidence["case01_rerun"] is False
