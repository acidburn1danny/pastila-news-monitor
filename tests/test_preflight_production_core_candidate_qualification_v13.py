"""Fail-closed V13 launch gate tests; no candidate is run."""
from __future__ import annotations

import json
import subprocess
import sys
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preflight_production_core_candidate_qualification_v13 as gate  # noqa: E402
import audit_production_core_v13_launcher_boundary as signed_gate  # noqa: E402
import execute_production_core_candidate_qualification_v13 as executor  # noqa: E402


def test_published_v13_source_and_matrix_close():
    gate.published_source_closure()
    gate.validate_matrix()


def test_output_must_be_empty_and_private(tmp_path):
    (tmp_path / "recovery").mkdir()
    (tmp_path / "private").mkdir()
    output = tmp_path / "output"
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    observed = gate.native_empty_output(output, tmp_path / "recovery", tmp_path / "private")
    assert observed["entries"] == 0
    (output / "unexpected").write_bytes(b"x")
    with pytest.raises(ValueError, match="not empty"):
        gate.native_empty_output(output, tmp_path / "recovery", tmp_path / "private")
    (output / "unexpected").unlink()
    output.chmod(0o755)
    with pytest.raises(ValueError, match="permissions rejected"):
        gate.native_empty_output(output, tmp_path / "recovery", tmp_path / "private")


def test_output_symlink_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="existing native Linux directory"):
        gate.native_empty_output(link, tmp_path / "recovery", tmp_path / "private")


def test_output_ancestor_symlink_rejected(tmp_path):
    real = tmp_path / "real"
    (real / "output").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="ancestor substitution"):
        gate.native_empty_output(link / "output", real, real)


def test_consume_mode_cannot_bypass_failed_preflight(tmp_path):
    script = ROOT / "scripts/launch_production_core_candidate_qualification_v13.py"
    result = subprocess.run([sys.executable, str(script), "--recovery-root", str(tmp_path),
                             "--private-root", str(tmp_path), "--backup-root", str(tmp_path),
                             "--unicode-root", str(tmp_path), "--output", str(tmp_path),
                             "--consume-attempt"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "output overlaps a protected input" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_published_tree_substitution_rejected(monkeypatch):
    monkeypatch.setattr(gate, "TREE", "0" * 40)
    with pytest.raises(ValueError, match="published V13 source tree mismatch"):
        gate.published_source_closure()


def test_signed_launcher_boundary_and_signature_substitution(tmp_path):
    assert signed_gate.audit()["ed25519_verification"] == "PASS"
    copied = tmp_path / "boundary"
    shutil.copytree(signed_gate.launcher_boundary.OUTPUT, copied)
    signature = copied / "binding.sig"
    raw = bytearray(signature.read_bytes())
    raw[0] ^= 1
    signature.write_bytes(raw)
    with pytest.raises(Exception):
        signed_gate.audit(copied)


def test_v13_validator_accepts_only_new_public_generation():
    art = ROOT / "docs/artifacts"
    snapshots = {name: (art / name).read_bytes() for name in executor.NAMES}
    executor.terminal_validator(snapshots)
    rows = executor.validate_and_map(*(json.loads(snapshots[name]) for name in executor.NAMES))
    assert len(rows) == 2400
    assert executor.validator.GENERATION_IDENTITY == "65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567"
    old_generation = json.loads((art / "production-core-successor-comparative-qualification-generation-v10.json").read_bytes())
    with pytest.raises(executor.validator.ExecutionAuthorityError, match="qualification_generation_identity mismatch"):
        executor.validator.validate_preflight(old_generation, *(json.loads(snapshots[name]) for name in executor.NAMES[1:]))


def test_v13_executor_projection_is_linux_native():
    source = executor.projected_mechanics()
    assert 'command = [\n            "bash",' in source
    assert '"scripts/execute_production_core_candidate_qualification_v13.py"' in source
    namespace = executor.build_namespace()
    assert namespace["RUNNER"].name == "production_core_candidate_qualification_runner_v12.py"
    assert namespace["PINNED_EXECUTION_MECHANISM"]["execution_authority_identity"] == signed_gate.launcher_boundary.AUTHORITY_ID
    assert namespace["GENERATION_IDENTITY"] == executor.validator.GENERATION_IDENTITY
