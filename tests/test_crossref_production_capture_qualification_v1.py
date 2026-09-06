"""Evidence closure for Milestone 10 Phase 5 offline qualification."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pastila_scout.crossref_pilot_offline_v1 as phase2

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / (
    "docs/artifacts/"
    "milestone10-phase5-bounded-crossref-production-capture-qualification-v1.json"
)
CLOSURE = ROOT / (
    "docs/artifacts/milestone10-closure-crossref-production-qualification-v1.json"
)
PHASE4_COMMIT = "54037f907f16ecb3aefe4fd7128b948d4f862d4c"
PHASE4_TREE = "87e9ce4619223bc9ba216ce5c96aa85c3386d70f"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase4_closure_records_exact_owner_designation() -> None:
    value = json.loads(CLOSURE.read_bytes())
    assert value == {
        "independent_public_review": "PASS",
        "phase": "Milestone 10 Phase 4 — Crossref Production Capture Qualification",
        "qualification_sha256": (
            "53a465a2983ea9f32cbd8c54ac9fc12c470e3c82d4e896f1690627c03a86f10b"
        ),
        "ref": "refs/heads/milestone10/phase4-crossref-production-qualification",
        "remaining_blockers": 0,
        "schema": "pastila-milestone-closure-v1",
        "status": "COMPLETE / PASS",
        "subject_commit": PHASE4_COMMIT,
        "subject_tree": PHASE4_TREE,
        "verdict": "PASS_OFFLINE_PRODUCTION_ORCHESTRATION",
    }
    assert (
        subprocess.check_output(
            ["git", "show", "-s", "--format=%T", PHASE4_COMMIT],
            cwd=ROOT,
            text=True,
        ).strip()
        == PHASE4_TREE
    )
    phase4_qualification = subprocess.check_output(
        [
            "git",
            "show",
            (
                PHASE4_COMMIT + ":docs/artifacts/"
                "milestone10-phase4-crossref-production-qualification-v1.json"
            ),
        ],
        cwd=ROOT,
    )
    assert (
        hashlib.sha256(phase4_qualification).hexdigest()
        == value["qualification_sha256"]
    )


def test_phase5_qualification_binds_exact_bytes_and_predecessor() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert value["schema"] == "pastila-crossref-production-capture-qualification-v1"
    assert value["verdict"] == "PASS_OFFLINE_ONE_SHOT_BOUNDARY"
    assert value["phase4_commit"] == PHASE4_COMMIT
    assert value["phase4_tree"] == PHASE4_TREE
    assert value["phase4_closure_sha256"] == sha256(CLOSURE)
    assert value["capture_authority_sha256"] == sha256(Path(phase2.__file__))
    assert value["implementation_sha256"] == sha256(
        ROOT / "src/pastila_scout/crossref_production_capture_v1.py"
    )
    assert value["implementation_test_sha256"] == sha256(
        ROOT / "tests/test_crossref_production_capture_v1.py"
    )
    assert value["qualification_test_sha256"] == sha256(Path(__file__))
    assert value["design_sha256"] == sha256(
        ROOT / "docs/milestone10-phase5-bounded-crossref-production-capture.md"
    )
    assert value["request_identity"] == phase2.frozen_request_identity_v1()
    assert (
        value["wire_request_sha256"]
        == hashlib.sha256(phase2.WIRE_REQUEST_BYTES).hexdigest()
    )
    assert set(value["invariants"].values()) == {"PASS"}
    assert value["zero_activity"] == {
        "crossref_requests": 0,
        "metadata_records_acquired": 0,
        "openalex_requests": 0,
        "scheduled_activations": 0,
    }


def test_production_capture_evidence_is_preserved_byte_for_byte_by_git() -> None:
    proof_root = ROOT / (
        ".pastila-runtime/milestone10-crossref-production-capture-v1"
    )
    paths = (
        proof_root / "attempt-consumed.json",
        proof_root / "completion.json",
        proof_root / "raw-capture/manifest.json",
        proof_root / "raw-capture/request.json",
        proof_root / "raw-capture/response-body.bin",
        proof_root / "raw-capture/response-headers.json",
        proof_root / "raw-capture/wire-request.http",
    )
    output = subprocess.check_output(
        ["git", "check-attr", "text", "eol", "--", *(str(p) for p in paths)],
        cwd=ROOT,
        text=True,
    )
    lines = output.splitlines()
    assert len(lines) == len(paths) * 2
    assert all(
        line.endswith((": text: unset", ": eol: unset"))
        for line in lines
    )


def test_phase5_does_not_change_existing_acceptance_selection_boundaries() -> None:
    changed = set(
        subprocess.check_output(
            ["git", "diff", "--name-only", PHASE4_COMMIT, "--"],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    changed.update(
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    phase5 = {
        path for path in changed if "phase5" in path or "production_capture" in path
    }
    assert phase5 == {
        "docs/artifacts/milestone10-phase5-bounded-crossref-production-capture-qualification-v1.json",
        "docs/milestone10-phase5-bounded-crossref-production-capture.md",
        "src/pastila_scout/crossref_production_capture_v1.py",
        "tests/test_crossref_production_capture_qualification_v1.py",
        "tests/test_crossref_production_capture_v1.py",
    }
    governed = phase5 | {
        ".gitattributes",
        "docs/artifacts/milestone10-closure-crossref-production-qualification-v1.json",
    }
    assert {
        path for path in changed if not path.startswith(".pastila-runtime/")
    } == governed
    assert "pyproject.toml" not in changed
    assert "tests/conftest.py" not in changed
