"""Adversarial offline tests for the Phase 6 admission boundary."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import pastila_scout.crossref_phase6_admission_v1 as phase6
from pastila_scout.crossref_phase6_admission_v1 import (
    CrossrefPhase6AdmissionError,
    execute_phase6_offline_admission_v1,
    recover_phase6_offline_admission_v1,
)


def test_exact_phase5_capture_is_admitted_atomically_offline(tmp_path: Path) -> None:
    root = tmp_path / "phase6"
    outcome = execute_phase6_offline_admission_v1(root)
    assert outcome.normalized_identity == phase6.NORMALIZED_IDENTITY
    assert outcome.batch_identity == (
        "370f8a1ec7bb8b35e08cd22348b85f987ac65533ebc62c8da71f8d9727abae13"
    )
    assert outcome.state_before_identity == (
        "62846329a1f032711c76f5120705b4c9a1237b92d5de6e9e273da8f25b41475b"
    )
    assert outcome.state_after_identity == (
        "9c56e9c48edb286da46cf08f263d6c9ef6a2ce13e1e572b36d4bf89465bfc92c"
    )
    assert outcome.record_count == 10
    assert outcome.identity == (
        "ca2f52ea4d26e4469fa3fbd4ad14b9a46474a090774a3a8930b3291c8ed9f549"
    )
    assert (root / "completion.json").read_bytes() == outcome.canonical_bytes
    assert not list(root.rglob("*.pending"))


def test_durable_state_binds_batch_and_phase5_provenance(tmp_path: Path) -> None:
    root = tmp_path / "phase6"
    outcome = execute_phase6_offline_admission_v1(root)
    state = json.loads((root / "integration-state.json").read_bytes())
    batch = json.loads((root / "integration-batch.json").read_bytes())
    assert state["applied_batch_identities"] == [outcome.batch_identity]
    assert len(state["records"]) == len(batch["records"]) == 10
    assert all(
        record["raw_capture_identity"] == phase6.RAW_CAPTURE_IDENTITY
        and record["normalized_identity"] == phase6.NORMALIZED_IDENTITY
        for record in state["records"]
    )
    assert hashlib.sha256(
        (root / "integration-state.json").read_bytes()
    ).hexdigest() == (outcome.state_after_identity)


def test_attempt_is_single_use_and_second_execution_cannot_redraw(
    tmp_path: Path,
) -> None:
    root = tmp_path / "phase6"
    execute_phase6_offline_admission_v1(root)
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    with pytest.raises(ValueError, match="execution root must be a new Path"):
        execute_phase6_offline_admission_v1(root)
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before


def test_interrupted_state_publication_recovers_without_redraw(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "phase6"
    real_link = phase6._durability.os.link

    def interrupt_state(source: object, destination: object) -> None:
        if Path(destination).name == "integration-state.json":
            raise OSError("simulated state interruption")
        real_link(source, destination)

    with monkeypatch.context() as context:
        context.setattr(phase6._durability.os, "link", interrupt_state)
        with pytest.raises(OSError, match="state interruption"):
            execute_phase6_offline_admission_v1(root)
    assert (root / "integration-state.json.pending").exists()
    assert not (root / "completion.json").exists()
    outcome = recover_phase6_offline_admission_v1(root)
    assert (root / "integration-state.json").read_bytes()
    assert (root / "completion.json").read_bytes() == outcome.canonical_bytes
    assert not list(root.rglob("*.pending"))


@pytest.mark.parametrize(
    "name",
    [
        "ARTIFACT_SHA256",
        "RAW_CAPTURE_IDENTITY",
        "NORMALIZED_IDENTITY",
        "_normalize",
        "_integrate",
    ],
)
def test_local_authority_rebinding_fails_before_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str
) -> None:
    monkeypatch.setattr(phase6, name, () if name == "ARTIFACT_SHA256" else "rebound")
    root = tmp_path / "phase6"
    with pytest.raises(CrossrefPhase6AdmissionError, match="runtime authority"):
        execute_phase6_offline_admission_v1(root)
    assert not root.exists()


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (phase6._integration, "_decode_document"),
        (phase6._integration, "_map_record"),
        (phase6._durability, "_read_regular_file"),
        (phase6._durability, "_atomic_publish_or_verify_existing"),
    ],
)
def test_dependency_rebinding_fails_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: object,
    name: str,
) -> None:
    monkeypatch.setattr(module, name, lambda *args: b"rebound")
    root = tmp_path / "phase6"
    with pytest.raises(CrossrefPhase6AdmissionError, match="runtime authority"):
        execute_phase6_offline_admission_v1(root)
    assert not root.exists()


def test_public_entry_has_no_caller_selected_capture_or_state() -> None:
    assert tuple(inspect.signature(execute_phase6_offline_admission_v1).parameters) == (
        "execution_root",
    )


def test_module_import_closure_is_network_inert() -> None:
    source = Path(phase6.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"http", "httpx", "requests", "socket", "sqlite3", "urllib"}
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert not imports.intersection(forbidden)
    assert "crossref_pilot_offline_v1" not in source
    assert "DirectCrossrefHttpsTransportV1" not in source
