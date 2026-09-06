import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/qualify_production_core_tokenizer_materialization_v1.sh"
BOUNDARY_FIXTURE = (
    ROOT / "tests/fixtures/production_core_tokenizer_launcher_boundary_v1.sh"
)


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if len(drive) != 1 or not drive.isascii() or not drive.isalpha():
        raise AssertionError("test checkout is not on a WSL-mounted Windows drive")
    relative = resolved.relative_to(resolved.anchor).as_posix()
    return f"/mnt/{drive}/{relative}"


@pytest.mark.skipif(shutil.which("wsl.exe") is None, reason="WSL2 unavailable")
def test_relocated_store_and_substitution_boundaries_execute_fail_closed() -> None:
    store = os.environ.get("PASTILA_TOKENIZER_TEST_STORE")
    if not store:
        pytest.skip("set PASTILA_TOKENIZER_TEST_STORE to the canonical offline store")
    launcher = _wsl_path(LAUNCHER)
    fixture = _wsl_path(BOUNDARY_FIXTURE)
    result = subprocess.run(
        [
            "wsl.exe",
            "-d",
            "Ubuntu-24.04",
            "-u",
            "root",
            "--",
            "timeout",
            "--signal=TERM",
            "--kill-after=10s",
            "150s",
            "bash",
            fixture,
            store,
            launcher,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=170,
    )
    assert result.returncode != 124, "Linux-side fixture timeout"
    assert result.returncode == 0, result.stderr
    assert result.stdout == "RELOCATED_AND_SUBSTITUTION_EXECUTABLE_PASS\n"
