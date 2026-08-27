"""One-shot packaged transport smoke; never loads a tokenizer or model."""

from __future__ import annotations

import json

from pastila_scout.wsl_execution_v1 import WslExecutionProfileV1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


def main() -> int:
    profile = WslExecutionProfileV1(
        profile_id="installed-build-transport-smoke-v1",
        distribution="Ubuntu-24.04",
        executable="/usr/bin/printf",
    )
    boundary = WslExecutionBoundaryV1_1(profile)
    invocation = boundary.build_invocation(
        consumer_id="installed-build-transport-smoke",
        authority_reference="zero-inference:installed-build",
        arguments=("%s", "PASTILA_INSTALLED_WSL_V1_1_OK"),
    )
    result = boundary.execute(invocation, timeout_seconds=30)
    value = {
        "command_identity": invocation.command_identity,
        "failure_code": result.receipt.failure_code.value
        if result.receipt.failure_code
        else None,
        "return_code": result.return_code,
        "stdout": result.stdout,
        "timed_out": result.receipt.timed_out,
    }
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return (
        0
        if result.succeeded and result.stdout == "PASTILA_INSTALLED_WSL_V1_1_OK"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
