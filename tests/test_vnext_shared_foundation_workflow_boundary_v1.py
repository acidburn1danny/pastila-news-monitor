from __future__ import annotations

import json
import os
from itertools import pairwise
from pathlib import Path

import pytest

import pastila_scout.vnext_foundation_v1 as foundation
from pastila_scout.vnext_foundation_v1 import (
    ContainmentError,
    DependencyError,
    ImmutableConflict,
    atomic_write,
    canonical_json,
    contained_path,
    object_identity,
    preflight,
    recover_interrupted_writes,
    scan_legacy_dependencies,
    sha256_bytes,
    validate_dependency_lock,
    write_immutable_receipt,
)
from pastila_scout.vnext_workflow_v1 import (
    IllegalTransition,
    ReplayConflict,
    TransitionRequest,
    WorkflowStore,
    apply_transition,
    new_workflow,
)


def request(previous: str = "DISCOVERED", resulting: str = "CAPTURED", *, key: str = "idem-1", operation: str = "op-1") -> TransitionRequest:
    return TransitionRequest("flow-1", operation, previous, resulting, "fixture", "PASS", "a" * 64, "b" * 64, "attempt-1", key, "2026-09-28T00:00:00Z", {"fixture": "v1"})


def lock_for(root: Path, *, child_identity: str | None = None, child_dependencies: list[str] | None = None) -> dict:
    (root / "root.txt").write_text("root", encoding="utf-8")
    (root / "child.txt").write_text("child", encoding="utf-8")
    return {
        "schema": "vnext-dependency-lock",
        "schema_version": 1,
        "roots": ["root"],
        "forbidden_dependencies": [],
        "dependencies": [
            {"id": "root", "path": "root.txt", "identity": sha256_bytes(b"root"), "depends_on": ["child"]},
            {"id": "child", "path": "child.txt", "identity": child_identity or sha256_bytes(b"child"), "depends_on": child_dependencies or []},
        ],
    }


def test_canonical_json_and_identities_are_deterministic():
    left = {"z": "știre", "a": [2, 1]}
    right = {"a": [2, 1], "z": "știre"}
    assert canonical_json(left) == canonical_json(right)
    assert object_identity(left) == object_identity(right)
    with pytest.raises(ValueError):
        canonical_json({"bad": float("nan")})


def test_legal_illegal_idempotent_and_conflicting_transitions():
    initial = new_workflow("flow-1")
    changed, receipt, wrote = apply_transition(initial, request())
    assert changed["state"] == "CAPTURED" and wrote is True
    replayed, prior, wrote = apply_transition(changed, request())
    assert replayed == changed and prior == receipt and wrote is False
    with pytest.raises(ReplayConflict):
        apply_transition(changed, request(previous="CAPTURED", resulting="GROUPED", operation="different"))
    with pytest.raises(IllegalTransition):
        apply_transition(initial, request(resulting="EXPORTED"))


def test_complete_canonical_disabled_voice_path_and_published_transition_binding():
    from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

    expected_states = {
        "DISCOVERED", "CAPTURED", "GROUPED", "SELECTED", "SOURCE_PACKET_READY",
        "EDITOR_PENDING", "EDITOR_DRAFT_READY", "STRUCTURAL_PASS", "STRUCTURAL_FAIL",
        "FACTUAL_REVIEW_PENDING", "ACCEPTED_SETUP", "SOURCE_FALLBACK", "ABSTAINED",
        "VOICE_DISABLED", "VOICE_PENDING", "VOICE_DRAFT_READY", "POLICY_REVIEW_PENDING",
        "APPROVED_FOR_FINAL", "REJECTED", "REVISION_REQUIRED", "FINAL_READY", "EXPORTED",
        "CAPTURE_FAILED", "SOURCE_PACKET_INVALID", "EDITOR_FAILED",
        "FACTUAL_ACCEPTANCE_FAILED", "VOICE_UNAVAILABLE", "FINAL_ASSEMBLY_FAILED",
    }
    required_transitions = {
        ("FACTUAL_REVIEW_PENDING", "ACCEPTED_SETUP"),
        ("FACTUAL_REVIEW_PENDING", "SOURCE_FALLBACK"),
        ("FACTUAL_REVIEW_PENDING", "ABSTAINED"),
        ("ACCEPTED_SETUP", "VOICE_DISABLED"),
        ("VOICE_DISABLED", "POLICY_REVIEW_PENDING"),
        ("APPROVED_FOR_FINAL", "FINAL_READY"),
        ("FINAL_READY", "EXPORTED"),
    }
    assert expected_states == set(STATES)
    assert required_transitions <= set(TRANSITIONS)
    path = [
        "DISCOVERED", "CAPTURED", "GROUPED", "SELECTED", "SOURCE_PACKET_READY",
        "EDITOR_PENDING", "EDITOR_DRAFT_READY", "STRUCTURAL_PASS", "FACTUAL_REVIEW_PENDING",
        "ACCEPTED_SETUP", "VOICE_DISABLED", "POLICY_REVIEW_PENDING", "APPROVED_FOR_FINAL",
        "FINAL_READY", "EXPORTED",
    ]
    state = new_workflow("flow-1")
    for index, (previous, resulting) in enumerate(pairwise(path), 1):
        transition = TransitionRequest(
            "flow-1", f"op-{index}", previous, resulting, "fixture", "PASS",
            object_identity({"step": index}), object_identity({"step": index + 1}),
            "attempt-1", f"idem-{index}",
        )
        state, _, changed = apply_transition(state, transition)
        assert changed is True and state["state"] == resulting


def test_atomic_store_interruption_and_recovery_do_not_invent_state(tmp_path: Path):
    store = WorkflowStore(tmp_path)
    original = store.create("flow-1")
    stale = tmp_path / ".flow-1.json.tmp-interrupted"
    stale.write_text('{"state":"EXPORTED"}', encoding="utf-8")
    assert store.load("flow-1") == original
    assert recover_interrupted_writes(tmp_path) == [stale.name]
    assert not stale.exists() and store.load("flow-1") == original
    updated, _, wrote = store.transition(request())
    assert wrote and updated["state"] == "CAPTURED"


def test_atomic_write_failure_has_no_partial_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    destination = tmp_path / "value.bin"
    atomic_write(destination, b"original", root=tmp_path)
    monkeypatch.setattr(foundation.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("interrupted")))
    with pytest.raises(OSError, match="interrupted"):
        atomic_write(destination, b"partial", root=tmp_path)
    assert destination.read_bytes() == b"original"
    assert list(tmp_path.glob(".*.tmp-*")) == []


def test_immutable_receipt_refuses_overwrite(tmp_path: Path):
    receipt = request().receipt()
    path = tmp_path / "receipt.json"
    first = write_immutable_receipt(path, receipt, root=tmp_path)
    assert first == receipt["receipt_identity"]
    with pytest.raises(ImmutableConflict):
        write_immutable_receipt(path, receipt, root=tmp_path)


def test_dependency_lock_preflight_and_negative_cases(tmp_path: Path):
    lock = lock_for(tmp_path)
    report = validate_dependency_lock(lock, root=tmp_path)
    assert report.checked == ("child", "root") and report.legacy_dependency_count == 0
    assert preflight(lock, root=tmp_path, required_capabilities=["atomic", "identity"])["status"] == "PASS"
    bad = json.loads(json.dumps(lock)); bad["dependencies"][1]["identity"] = "0" * 64
    with pytest.raises(DependencyError, match="identity mismatch"):
        validate_dependency_lock(bad, root=tmp_path)
    undeclared = json.loads(json.dumps(lock)); undeclared["dependencies"][1]["depends_on"] = ["missing"]
    with pytest.raises(DependencyError, match="undeclared"):
        validate_dependency_lock(undeclared, root=tmp_path)
    forbidden = json.loads(json.dumps(lock)); forbidden["forbidden_dependencies"] = ["child"]
    with pytest.raises(DependencyError, match="forbidden dependencies selected"):
        validate_dependency_lock(forbidden, root=tmp_path)


def test_external_path_and_hardlink_are_rejected(tmp_path: Path):
    outside = tmp_path.parent / "outside-vnext-foundation.txt"
    outside.write_text("outside", encoding="utf-8")
    try:
        with pytest.raises(ContainmentError):
            contained_path(tmp_path, outside)
        linked = tmp_path / "linked.txt"
        os.link(outside, linked)
        lock = {
            "schema": "vnext-dependency-lock", "schema_version": 1,
            "roots": ["linked"], "forbidden_dependencies": [],
            "dependencies": [{"id": "linked", "path": "linked.txt", "identity": sha256_bytes(b"outside"), "depends_on": []}],
        }
        with pytest.raises(ContainmentError, match="hardlinked"):
            validate_dependency_lock(lock, root=tmp_path)
    finally:
        outside.unlink(missing_ok=True)


def test_symlink_escape_is_rejected(tmp_path: Path):
    outside = tmp_path.parent / "outside-vnext-symlink.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "escape.txt"
    try:
        try:
            link.symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"symlinks unavailable on this platform: {exc}")
        lock = {
            "schema": "vnext-dependency-lock", "schema_version": 1,
            "roots": ["escape"], "forbidden_dependencies": [],
            "dependencies": [{"id": "escape", "path": "escape.txt", "identity": sha256_bytes(b"outside"), "depends_on": []}],
        }
        with pytest.raises(ContainmentError):
            validate_dependency_lock(lock, root=tmp_path)
    finally:
        link.unlink(missing_ok=True); outside.unlink(missing_ok=True)


def test_direct_transitive_legacy_and_false_positive_regression(tmp_path: Path):
    benign = tmp_path / "benign.py"
    benign.write_text("# coherent with legacy reporting in the tests\n", encoding="utf-8")
    assert scan_legacy_dependencies(tmp_path) == []
    direct = tmp_path / "direct.py"
    direct.write_text("ROOT = '/root/pf9-runtime'\n", encoding="utf-8")
    findings = scan_legacy_dependencies(tmp_path)
    assert len(findings) == 1 and findings[0]["path"] == "direct.py"
    direct.unlink()
    child = tmp_path / "child.txt"; child.write_text("child", encoding="utf-8")
    root_file = tmp_path / "root.txt"; root_file.write_text("root", encoding="utf-8")
    lock = {
        "schema": "vnext-dependency-lock", "schema_version": 1, "roots": ["root"], "forbidden_dependencies": [],
        "dependencies": [
            {"id": "root", "path": "root.txt", "identity": sha256_bytes(b"root"), "depends_on": ["legacy-runtime"]},
            {"id": "legacy-runtime", "path": "child.txt", "identity": sha256_bytes(b"child"), "depends_on": []},
        ],
    }
    with pytest.raises(DependencyError, match="legacy dependencies"):
        validate_dependency_lock(lock, root=tmp_path)


def test_observation_metadata_does_not_change_semantic_receipt_identity():
    first = request()
    second = TransitionRequest(**{**first.__dict__, "observed_at": "2027-01-01T00:00:00Z", "provenance": {"host": "other"}})
    assert first.receipt()["receipt_identity"] == second.receipt()["receipt_identity"]


def test_fixture_contract_has_all_required_cases():
    fixtures = json.loads(Path("docs/artifacts/vnext-shared-foundation-workflow-boundary-v1-fixtures.json").read_text(encoding="utf-8"))
    assert len(fixtures["cases"]) == 19
    assert {case["id"] for case in fixtures["cases"]} >= {"LEGAL_TRANSITION", "CONFLICTING_REPLAY", "BENIGN_LEGACY_TEXT", "RECOVERY_NO_STATE_INVENTION"}
