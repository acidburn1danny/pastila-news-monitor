"""Fail-closed V15 pre-consumption checks; no candidate execution."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preflight_production_core_candidate_qualification_v15 as gate  # noqa: E402


def test_published_checkpoint_scope_and_bytes() -> None:
    gate.published_source_closure()


def test_published_source_drift_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = gate.PUBLIC_FILES
    monkeypatch.setattr(gate, "PUBLIC_FILES", (*original, "tests/extra.py"))
    with pytest.raises(ValueError, match="scope mismatch"):
        gate.published_source_closure()


def test_output_must_be_empty_native_ext4(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir(mode=0o700)
    assert gate.empty_output(output, (ROOT,))["entries"] == 0
    (output / "attempt.json").write_text("{}")
    with pytest.raises(ValueError, match="not empty"):
        gate.empty_output(output, (ROOT,))


def test_output_symlink_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(output, target_is_directory=True)
    with pytest.raises(ValueError, match="substitution|native WSL root"):
        gate.empty_output(link, (ROOT,))


def test_wrong_snapshot_rejected_before_authority_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "published_source_closure", lambda: None)
    bad = Path("/root/failed-windows-replay")
    with pytest.raises(ValueError, match="snapshot path mismatch"):
        gate.preflight(ROOT, ROOT, ROOT, ROOT, ROOT, ROOT, bad, ROOT, ROOT)
