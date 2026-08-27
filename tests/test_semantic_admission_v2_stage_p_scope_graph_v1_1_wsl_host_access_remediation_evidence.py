from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-wsl-host-access-remediation-evidence"
FAILED_RUN = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v1-evidence"


def test_preserved_remediation_files_have_exact_hashes() -> None:
    expected = {
        "preflight.json": "12d7fd51c271598f1bb1934797de4b20315ef6a75e2aed2905beed3a52765f26",
        "report.md": "61f412617a03e442eee6d7c14a0c4246ad7063c8b1cd82ce631833131f2b13bc",
    }
    actual = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in EVIDENCE.iterdir()
        if path.is_file()
    }
    assert actual == expected


def test_diagnosis_is_bound_to_the_preserved_failed_run() -> None:
    value = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert ROOT / value["preserved_failed_probe"] == FAILED_RUN
    assert FAILED_RUN.is_dir()
    diagnosis = value["failure_diagnosis"]
    assert diagnosis == {
        "recorded_error": "Wsl/Service/E_ACCESSDENIED",
        "classification": "CALLER_EXECUTION_CONTEXT_RESTRICTION",
        "distribution_corruption": False,
        "repository_runtime_defect_found": False,
    }


def test_receipt_is_historical_zero_inference_and_grants_no_authority() -> None:
    value = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert value["result"] == "PASS"
    assert value["mode"] == "ZERO_INFERENCE_HOST_ACCESS_PREFLIGHT"
    assert value["host_checks"]["noop_launch"] == "PASS"
    assert value["host_checks"]["bound_python_executable"] == "PASS"
    assert value["host_checks"]["mounted_runner_readable"] == "PASS"
    assert all(count == 0 for count in value["execution_counts"].values())
    assert not any(value["authority"].values())
