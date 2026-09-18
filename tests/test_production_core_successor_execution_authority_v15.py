"""V15 production driver closure and zero-attempt authority properties."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from pastila_scout import production_core_wsl_driver_snapshot_v15 as drivers

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import materialize_production_core_successor_execution_authority_v15 as authority  # noqa: E402


def test_driver_manifest_rejects_mutable_and_changed_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "drivers"
    root.mkdir()
    payload = root / "driver.bin"
    payload.write_bytes(b"pinned-driver")
    rows = [["driver.bin", len(b"pinned-driver"), hashlib.sha256(b"pinned-driver").hexdigest()]]
    expected = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    monkeypatch.setattr(drivers, "EXPECTED_FILES", 1)
    monkeypatch.setattr(drivers, "EXPECTED_MANIFEST", expected)
    with pytest.raises(ValueError, match="root is writable"):
        drivers.manifest(root)
    payload.chmod(0o444)
    root.chmod(0o555)
    try:
        assert drivers.manifest(root)["manifest_identity"] == expected
        payload.chmod(0o644)
        with pytest.raises(ValueError, match="writable"):
            drivers.manifest(root)
        payload.write_bytes(b"changed-driver")
        payload.chmod(0o444)
        with pytest.raises(ValueError, match="manifest mismatch"):
            drivers.manifest(root)
    finally:
        root.chmod(0o755)
        payload.chmod(0o644)


def test_authority_binding_has_zero_attempt_and_terminal_identity() -> None:
    artifact = {
        "authority_identity": "a" * 64,
        "builder_sha256": "b" * 64,
        "driver_snapshot": {"manifest_identity": drivers.EXPECTED_MANIFEST},
        "isolated_gpu_probe": {"cuda_available": True},
        "source_sha256": {},
    }
    binding = authority.binding_for(artifact, b"authority")
    assert binding["predecessor_v14_attempt_identity"] == authority.design.ATTEMPT
    assert binding["predecessor_v14_terminal_failure_identity"] == authority.design.FAILURE
    assert binding["driver_snapshot"]["manifest_identity"] == drivers.EXPECTED_MANIFEST
    assert binding["new_attempt_consumption"] == 0
    assert binding["new_candidate_execution"] == 0
    assert binding["adjudication"] is False and binding["promotion"] is False


def test_production_shell_has_readonly_driver_mount_and_no_v14_rewrite() -> None:
    shell = (ROOT / "scripts/run_production_core_candidate_qualification_v15.sh").read_text()
    assert 'mount --bind "$DRIVER_ROOT" "$ROOTFS/usr/lib/wsl/drivers"' in shell
    assert 'mount -o remount,bind,ro "$ROOTFS/usr/lib/wsl/drivers"' in shell
    assert '/root/pf9-v15-wsl-drivers-snapshot' in shell and '2096:21113' in shell
    assert 'python3 -B "$WORK/manifest.py" --root "$ROOTFS/usr/lib/wsl/drivers"' in shell
    assert 'QUALIFICATION_GENERATION_IDENTITY="$GENERATION_ID"' in shell
    assert 'QUALIFICATION_IDENTITY="$QUALIFICATION_ID"' in shell
