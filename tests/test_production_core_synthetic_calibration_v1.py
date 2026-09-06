import inspect
import subprocess
import sys

import pytest

from pastila_scout import production_core_synthetic_calibration_v1 as calibration


def test_structural_probe_is_candidate_free_and_deterministic() -> None:
    first = calibration.structural_probe(rounds=2)
    second = calibration.structural_probe(rounds=2)
    assert first["result_sha256"] == second["result_sha256"]
    assert first["output_bytes"] == second["output_bytes"]
    assert first["elapsed_ns"] > 0
    assert first["peak_rss_bytes"] > 0


def test_invalid_probe_bounds_fail_closed() -> None:
    for value in (0, 10_001, True):
        with pytest.raises(ValueError):
            calibration.structural_probe(rounds=value)


def test_calibrator_has_no_candidate_or_network_import_path() -> None:
    source = inspect.getsource(calibration)
    for forbidden in (
        "experimental_core_v1_1",
        "experimental_core_v1_2",
        "socket",
        "httpx",
        "requests",
        "urllib",
    ):
        assert forbidden not in source


def test_real_script_entry_executes_isolated_worker() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(calibration.Path(calibration.__file__).resolve()),
            "--structural-worker",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert '"result_sha256"' in result.stdout
