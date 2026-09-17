"""Adversarial checks for the recovery-bound zero-attempt V12 authority."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import materialize_production_core_successor_execution_authority_v12 as authority  # noqa: E402
import audit_production_core_successor_execution_authority_v12 as auditor  # noqa: E402


def test_source_closure_binds_published_commit_tree_and_runner(monkeypatch):
    closure = authority.source_closure()
    assert closure["src/pastila_scout/production_core_candidate_qualification_runner_v12.py"] == authority.RUNNER
    assert "scripts/materialize_production_core_v12_recovery_runtime.py" in closure
    assert "scripts/audit_production_core_v12_recovery_runtime.py" in closure
    monkeypatch.setattr(authority, "TREE", "0" * 40)
    with pytest.raises(ValueError, match="source commit or tree mismatch"):
        authority.source_closure()


def test_source_closure_rejects_unrelated_or_divergent_published_history(monkeypatch):
    original_git = authority.git
    original_ancestor = authority.ancestor

    def substituted_ref(*args):
        if args == ("rev-parse", "refs/remotes/origin/successor/core-v2-v12-runner-binding-remediation"):
            return b"f" * 40
        return original_git(*args)

    monkeypatch.setattr(authority, "git", substituted_ref)
    monkeypatch.setattr(authority, "ancestor", lambda older, newer: False if newer == "f" * 40 else original_ancestor(older, newer))
    with pytest.raises(ValueError, match="published recovery branch mismatch"):
        authority.source_closure()

    monkeypatch.setattr(authority, "ancestor", lambda older, newer: older == authority.COMMIT)
    with pytest.raises(ValueError, match="local and published histories diverge"):
        authority.source_closure()


def test_source_closure_accepts_only_checkout_newline_conversion_for_public_key(monkeypatch, tmp_path):
    original = authority.PUBLIC_KEY.read_bytes()
    key = tmp_path / "public.pem"
    monkeypatch.setattr(authority, "PUBLIC_KEY", key)
    key.write_bytes(original.replace(b"\r\n", b"\n"))
    authority.source_closure()
    key.write_bytes(original + b"extra")
    with pytest.raises(ValueError, match="signing public key identity mismatch"):
        authority.source_closure()


def test_binding_explicitly_carries_v12_state_and_rejects_legacy_identity():
    body = {
        "authority_identity": "a" * 64,
        "builder_sha256": "b" * 64,
        "runtime_object_closure": {"executor_projection_sha256": "c" * 64},
    }
    binding = authority.binding_for(body, b"authority")
    assert binding["bound_source_commit"] == authority.COMMIT
    assert binding["bound_source_tree"] == authority.TREE
    assert binding["runner_v12_identity"] == authority.RUNNER
    assert binding["recovery_resolution_identity"] == authority.RESOLUTION
    assert binding["candidate_execution"] == binding["successor_attempt_consumption"] == 0
    assert binding["adjudication"] is binding["promotion"] is False
    assert "predecessor_terminal_disposition_identity" not in binding
    assert "authority_identities" not in binding


def test_runtime_closure_rejects_missing_hidden_and_stale_resolution(tmp_path):
    with pytest.raises(ValueError, match="hidden or missing state"):
        authority.runtime_closure(tmp_path)
    for name in authority.EXPECTED_ENTRIES:
        item = tmp_path / name
        if name.endswith(".json"):
            item.write_text("{}", encoding="utf-8")
        else:
            item.mkdir()
    with pytest.raises(ValueError, match="canonical V12 recovery identity mismatch"):
        authority.runtime_closure(tmp_path)
    (tmp_path / "hidden-state.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hidden or missing state"):
        authority.runtime_closure(tmp_path)


def test_materialize_fails_closed_if_output_already_exists(tmp_path):
    output = tmp_path / "authority"
    output.mkdir()
    with pytest.raises(ValueError, match="output root must be new"):
        authority.materialize(tmp_path, output, tmp_path / "missing.pem")


def test_signed_authority_rejects_mutated_binding_signature_builder_and_state(tmp_path):
    source = os.environ.get("PASTILA_V12_AUTHORITY_ROOT")
    if not source:
        pytest.skip("signed authority artifact not yet materialized")
    source_root = Path(source)
    recovery_root = Path(os.environ["PASTILA_V12_RECOVERY_ROOT"])
    assert auditor.audit(source_root, recovery_root, recompute=False)["ed25519_verification"] == "PASS"
    for filename in ("binding.json", "binding.sig", "builder-source.py", "authority.json"):
        target = tmp_path / filename.replace(".", "-")
        shutil.copytree(source_root, target)
        item = target / filename
        raw = item.read_bytes()
        item.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with pytest.raises((ValueError, subprocess.CalledProcessError, json.JSONDecodeError)):
            auditor.audit(target, recovery_root, recompute=False)


def test_signed_authority_rejects_extra_artifact(tmp_path):
    source = os.environ.get("PASTILA_V12_AUTHORITY_ROOT")
    if not source:
        pytest.skip("signed authority artifact not yet materialized")
    target = tmp_path / "extra"
    shutil.copytree(Path(source), target)
    (target / "hidden.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact closure mismatch"):
        auditor.audit(target, Path(os.environ["PASTILA_V12_RECOVERY_ROOT"]), recompute=False)
