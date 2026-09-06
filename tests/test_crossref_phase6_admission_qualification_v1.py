"""Qualification evidence bindings for Milestone 10 Phase 6."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pastila_scout.crossref_phase6_admission_v1 as phase6

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / (
    "docs/artifacts/milestone10-phase6-crossref-production-admission-qualification-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase6_qualification_binds_exact_components() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert value["schema"] == "pastila-crossref-phase6-admission-qualification-v1"
    assert value["verdict"] == "PASS_OFFLINE_PHASE5_CAPTURE_ADMISSION"
    assert value["implementation_sha256"] == _sha(Path(phase6.__file__))
    assert value["implementation_test_sha256"] == _sha(
        ROOT / "tests/test_crossref_phase6_admission_v1.py"
    )
    historical_test = subprocess.check_output(
        [
            "git",
            "show",
            "31093ab8bc4a0a1ed147a1b0d9932b55424012ac:"
            + Path(__file__).relative_to(ROOT).as_posix(),
        ],
        cwd=ROOT,
    )
    assert (
        value["qualification_test_sha256"]
        == hashlib.sha256(historical_test).hexdigest()
    )
    assert value["document_sha256"] == _sha(
        ROOT / "docs/milestone10-phase6-crossref-production-admission.md"
    )
    assert value["phase5_proof_tip"] == phase6.PROOF_TIP
    assert value["phase5_proof_tree"] == phase6.PROOF_TREE
    assert value["phase5_capture_commit"] == phase6.CAPTURE_COMMIT
    assert value["phase5_capture_tree"] == phase6.CAPTURE_TREE
    assert value["phase5_execution_qualification_sha256"] == (
        phase6.EXECUTION_QUALIFICATION_SHA256
    )
    assert value["request_identity"] == phase6.REQUEST_IDENTITY
    assert value["raw_capture_identity"] == phase6.RAW_CAPTURE_IDENTITY
    assert value["normalized_identity"] == phase6.NORMALIZED_IDENTITY
    assert set(value["invariants"].values()) == {"PASS"}
    assert value["zero_activity"] == {
        "crossref_requests": 0,
        "openalex_requests": 0,
        "scheduled_activations": 0,
        "downstream_publications": 0,
    }


def test_phase6_files_do_not_change_test_selection_or_dependencies() -> None:
    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / "tests/conftest.py").is_file()
    source = Path(phase6.__file__).read_text(encoding="utf-8")
    assert "crossref_pilot_offline_v1" not in source
    assert "execute_one_shot_capture_v1" not in source
