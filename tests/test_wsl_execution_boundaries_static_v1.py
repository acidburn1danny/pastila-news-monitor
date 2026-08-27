from __future__ import annotations

from pastila_scout.wsl_execution_v1 import (
    WslExecutionBoundaryV1,
    canonical_model_profile_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


def test_canonical_path_and_command_are_deterministic_without_launch() -> None:
    profile = canonical_model_profile_v1()
    boundary = WslExecutionBoundaryV1(profile)
    invocation = boundary.build_invocation(
        consumer_id="static-verification",
        authority_reference="zero-inference:test",
        arguments=(windows_path_to_wsl_v1(r"C:\Projects\fixture.json"),),
    )

    assert invocation.command[:5] == (
        "wsl.exe",
        "-d",
        "Ubuntu-24.04",
        "--",
        profile.executable,
    )
    assert invocation.profile_identity == profile.identity


def test_v1_1_preserves_frozen_command_construction_without_launch() -> None:
    profile = canonical_model_profile_v1()
    kwargs = {
        "consumer_id": "static-verification",
        "authority_reference": "zero-inference:equivalence",
        "arguments": ("/mnt/c/fixture.py", "--literal=$()"),
    }

    frozen = WslExecutionBoundaryV1(profile).build_invocation(**kwargs)
    successor = WslExecutionBoundaryV1_1(profile).build_invocation(**kwargs)

    assert successor == frozen
    assert successor.command_identity == frozen.command_identity
