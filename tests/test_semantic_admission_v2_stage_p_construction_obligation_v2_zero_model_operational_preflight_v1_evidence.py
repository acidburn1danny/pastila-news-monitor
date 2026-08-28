from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / ".semantic-admission-v2-stage-p-construction-obligation-v2-zero-model-operational-preflight-v1-evidence"
)


def test_frozen_zero_model_preflight_bundle_is_exact():
    manifest = json.loads((EVIDENCE / "manifest.json").read_bytes())
    fields = manifest["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == manifest["canonical_identity"]
    )
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == expected
    worker = json.loads((EVIDENCE / "worker-report.json").read_bytes())
    host = json.loads((EVIDENCE / "host-receipt.json").read_bytes())
    wsl = json.loads((EVIDENCE / "wsl-execution-receipt.json").read_bytes())
    assert manifest["verdict"] == "PASS"
    assert worker["drvfs_hardlink_publication"] == "PASS"
    assert worker["child_reaped"] is worker["child_proc_absent"] is True
    assert (
        worker["tokenizer_loads"],
        worker["model_loads"],
        worker["generation_calls"],
    ) == (0, 0, 0)
    assert wsl["return_code"] == 0 and wsl["failure_code"] is None
    assert host["worker_report_identity"] == worker["report_identity"]
    assert (
        host["wsl_execution_receipt_sha256"]
        == manifest["files"]["wsl-execution-receipt.json"]
    )
    assert manifest["authority"]["generation_authority_receipt_issued"] is False
