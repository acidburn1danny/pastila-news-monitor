"""Git-only verifier for the consumed Case 01 one-shot attempt freeze."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
    "case01-successor-execution-attempt-v1"
)
FREEZE_IDENTITY = "947e0b92c3f4eeffe039f1416cca220d2d68ca76e65ffce4e4807c39a472fea7"
WSL_SHA256 = "e58936d89df066e5a79eab14a2551ce291eb2e1a2130004a3eaffded220beb8d"
HOST_SHA256 = "7ebc3fc0c367796aed76673904040ba921b0208b5f5dc5ce33345e9b5082af61"


def verify(*, project_root: Path) -> dict[str, object]:
    root = project_root.resolve(strict=True) / RELATIVE
    if {path.name for path in root.iterdir() if path.is_file()} != {
        "wsl-execution-receipt.json", "host-reconciliation.json", "manifest.json"
    }:
        raise RuntimeError("CASE01_EXECUTION_FREEZE_FILE_SET_MISMATCH")
    raw_wsl = root.joinpath("wsl-execution-receipt.json").read_bytes()
    raw_host = root.joinpath("host-reconciliation.json").read_bytes()
    raw_manifest = root.joinpath("manifest.json").read_bytes()
    wsl = _canonical_object(raw_wsl)
    host = _canonical_object(raw_host)
    manifest = _canonical_object(raw_manifest)
    if hashlib.sha256(raw_wsl).hexdigest() != WSL_SHA256:
        raise RuntimeError("CASE01_WSL_RECEIPT_HASH_MISMATCH")
    if hashlib.sha256(raw_host).hexdigest() != HOST_SHA256:
        raise RuntimeError("CASE01_HOST_RECONCILIATION_HASH_MISMATCH")
    if (
        wsl["return_code"] != 1 or wsl["timed_out"] is not False
        or wsl["failure_code"] != "WSL_PROCESS_NONZERO_EXIT"
        or host["status"] != "TRANSPORT_FAILURE" or host["retry_count"] != 0
        or host["wsl_execution_receipt_sha256"] != WSL_SHA256
        or host["linux_supervisor_receipt_identity"] is not None
    ):
        raise RuntimeError("CASE01_TRANSPORT_CLASSIFICATION_MISMATCH")
    fields = manifest["identity_derivation"]["ordered_utf8_fields"]
    if hashlib.sha256("\n".join(fields).encode()).hexdigest() != FREEZE_IDENTITY:
        raise RuntimeError("CASE01_EXECUTION_FREEZE_IDENTITY_MISMATCH")
    if (
        manifest["freeze_identity"] != FREEZE_IDENTITY
        or manifest["attempt"] != {
            "attempt_ceiling": 1, "attempt_consumed": True,
            "consumed_attempts": 1, "remaining_attempts": 0, "retry_count": 0,
        }
        or manifest["execution"]["model_load_result"] != "NOT_STARTED"
        or manifest["execution"]["generation_result"] != "NOT_STARTED"
        or manifest["execution"]["compatibility_result"] != "NOT_REACHED"
        or manifest["evidence"]["raw_stdout_available"] is not False
        or manifest["evidence"]["raw_stderr_available"] is not False
        or any(manifest["subsequent_authority"].values())
    ):
        raise RuntimeError("CASE01_EXECUTION_FREEZE_SEMANTICS_MISMATCH")
    return manifest


def _canonical_object(raw: bytes) -> dict[str, object]:
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if type(value) is not dict or raw != (
        json.dumps(value, ensure_ascii=True, sort_keys=True,
                   separators=(",", ":"), allow_nan=False) + "\n"
    ).encode():
        raise RuntimeError("CASE01_EXECUTION_FREEZE_CANONICAL_BYTES_REQUIRED")
    return value


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        raise SystemExit("usage: verifier PROJECT_ROOT")
    manifest = verify(project_root=Path(arguments[0]))
    print(json.dumps({
        "result": "PASS", "freeze_identity": manifest["freeze_identity"],
        "status": manifest["execution"]["status"],
        "consumed_attempts": manifest["attempt"]["consumed_attempts"],
        "remaining_attempts": manifest["attempt"]["remaining_attempts"],
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
