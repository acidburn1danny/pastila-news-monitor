from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / (
    ".semantic-admission-v2-stage-p-construction-obligation-v2-v1-1-"
    "one-shot-model-load-validation-v1-evidence"
)
EXPECTED_RESULT_IDENTITY = (
    "3fb50778db93e9310b6bea499190ff3011fb9aeb47573f24e4e8c93034c3dc26"
)
EXPECTED_COMPATIBILITY_IDENTITY = (
    "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f"
)


def test_manifest_identity_and_all_raw_files_are_exact() -> None:
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    derived = hashlib.sha256(
        "\n".join(manifest["identity_derivation"]["ordered_utf8_fields"]).encode()
    ).hexdigest()
    assert derived == manifest["canonical_identity"] == EXPECTED_RESULT_IDENTITY
    for entry in manifest["files"]:
        raw = (EVIDENCE / entry["path"]).read_bytes()
        assert len(raw) == entry["size"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


def test_single_attempt_completed_with_compatibility_and_cleanup() -> None:
    result = json.loads((EVIDENCE / "result.json").read_text("utf-8"))
    assert result["attempts_authorized"] == result["attempts_consumed"] == 1
    assert result["status"] == "LOAD_ONLY_COMPLETED_COMPATIBILITY_VALIDATED_AND_RELEASED"
    assert result["model_load_completed"] is True
    assert result["adapter_compatibility_validated"] is True
    assert result["adapter_compatibility_receipt_identity"] == EXPECTED_COMPATIBILITY_IDENTITY
    assert result["cleanup_completed"] is True
    assert result["raw_stdout_persisted"] is result["raw_stderr_persisted"] is True
    assert (
        result["generation_calls"], result["retry_calls"], result["fallback_calls"],
        result["probe_calls"], result["stage_c_entries"],
    ) == (0, 0, 0, 0, 0)
    assert result["generation_readiness"] == "NOT_GRANTED"
    assert result["runtime_or_production_authority"] is False


def test_transport_and_lifecycle_bind_exact_authority_and_compatibility() -> None:
    receipt = json.loads((EVIDENCE / "wsl-execution-receipt.json").read_text("utf-8"))
    assert receipt["authority_reference"] == (
        "3e46f6992384abbd74219451478ead0b964a7499325caf728803bb357f3b050c"
    )
    assert receipt["return_code"] == 0 and receipt["timed_out"] is False
    assert receipt["failure_code"] is None
    assert hashlib.sha256((EVIDENCE / "raw-stdout.txt").read_bytes()).hexdigest() == receipt["stdout_sha256"]
    assert hashlib.sha256((EVIDENCE / "raw-stderr.txt").read_bytes()).hexdigest() == receipt["stderr_sha256"]

    lifecycle = [
        json.loads(path.read_text("utf-8"))
        for path in sorted((EVIDENCE / "lifecycle").glob("*.json"))
    ]
    assert [item["event"] for item in lifecycle] == [
        "MODEL_LOAD_STARTED", "MODEL_LOAD_COMPLETED",
        "MODEL_LOAD_CLEANUP_COMPLETED", "MODEL_LOAD_SUPERVISOR_TERMINAL",
    ]
    assert lifecycle[1]["adapter_compatibility_receipt_identity"] == EXPECTED_COMPATIBILITY_IDENTITY
    assert lifecycle[-1]["adapter_compatibility_validated"] is True
    assert lifecycle[-1]["child_exitcode"] == 0


def test_raw_stderr_preserves_only_expected_host_visible_warning() -> None:
    stderr = (EVIDENCE / "raw-stderr.txt").read_text("utf-8")
    assert "tied weights mapping" in stderr
    assert "missing adapter keys" not in stderr.lower()
    assert (EVIDENCE / "raw-stdout.txt").read_bytes() == b""
