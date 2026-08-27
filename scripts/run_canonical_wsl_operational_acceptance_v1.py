"""Run bounded transport-only live checks for the canonical WSL boundary.

No tokenizer or model is loaded. No retry is performed. Results are printed as
canonical JSON for capture by the separately frozen acceptance evidence.
"""
from __future__ import annotations

import concurrent.futures
import json
import time
from pathlib import Path

from pastila_scout.wsl_execution_v1 import WslExecutionBoundaryV1, WslExecutionProfileV1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


ROOT = Path(__file__).resolve().parents[1]
MARKER = "PASTILA_șțâ_transport_OK"


def profile(profile_id: str, executable: str, distribution: str = "Ubuntu-24.04"):
    return WslExecutionProfileV1(profile_id, distribution, executable)


def invoke(boundary, marker: str, arguments: tuple[str, ...], timeout: float = 10):
    invocation = boundary.build_invocation(
        consumer_id="operational-acceptance-live-v1",
        authority_reference=f"transport-only:{marker}",
        arguments=arguments,
    )
    result = boundary.execute(invocation, timeout_seconds=timeout)
    return {
        "command_identity": invocation.command_identity,
        "return_code": result.return_code,
        "timed_out": result.receipt.timed_out,
        "failure_code": result.receipt.failure_code.value if result.receipt.failure_code else None,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed_ms": result.receipt.elapsed_ms,
    }


def main() -> int:
    results = {}
    printf = WslExecutionBoundaryV1(profile("live-printf-v1", "/usr/bin/printf"))
    results["transport_unicode"] = invoke(printf, "unicode", ("%s", MARKER))
    results["missing_distribution_v1_1"] = invoke(
        WslExecutionBoundaryV1_1(profile("missing-distro-v1", "/usr/bin/true", "Pastila-Missing-Distro")),
        "missing-distribution",
        (),
    )
    results["missing_executable_v1_1"] = invoke(
        WslExecutionBoundaryV1_1(profile("missing-executable-v1", "/pastila/missing-executable")),
        "missing-executable",
        (),
    )

    def concurrent_check(index: int):
        return invoke(printf, f"concurrent-{index}", ("%s", f"transport-{index}"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results["concurrency"] = list(pool.map(concurrent_check, range(4)))

    marker_path = ROOT / ".wsl-operational-timeout-orphan-marker"
    resolved_root = ROOT.resolve()
    if marker_path.resolve().parent != resolved_root:
        raise RuntimeError("OPERATIONAL_MARKER_OUTSIDE_WORKSPACE")
    marker_path.unlink(missing_ok=True)
    linux_marker = "/mnt/c/Projects/pastila-news-monitor/.wsl-operational-timeout-orphan-marker"
    python = WslExecutionBoundaryV1(profile("live-timeout-v1", "/usr/bin/python3"))
    code = (
        "import pathlib,time;time.sleep(1);"
        f"pathlib.Path({linux_marker!r}).write_text('orphan',encoding='utf-8')"
    )
    results["timeout"] = invoke(python, "timeout-orphan", ("-c", code), timeout=0.1)
    time.sleep(1.5)
    results["timeout_orphan_observed"] = marker_path.exists()
    marker_path.unlink(missing_ok=True)

    results["pass_conditions"] = {
        "transport_unicode": results["transport_unicode"]["stdout"] == MARKER,
        "missing_distribution_typed": results["missing_distribution_v1_1"]["failure_code"]
        == "WSL_DISTRIBUTION_UNAVAILABLE",
        "missing_executable_typed": results["missing_executable_v1_1"]["failure_code"]
        == "WSL_EXECUTABLE_UNAVAILABLE",
        "concurrency": all(item["return_code"] == 0 for item in results["concurrency"]),
        "timeout_typed": results["timeout"]["failure_code"] == "WSL_EXECUTION_TIMEOUT",
        "no_timeout_orphan": not results["timeout_orphan_observed"],
    }
    # Keep the capture envelope compatible with Windows consoles configured
    # for a legacy code page; the decoded payload assertions above still
    # prove Unicode round-tripping.
    print(json.dumps(results, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0 if all(results["pass_conditions"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
