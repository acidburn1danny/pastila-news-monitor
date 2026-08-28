"""Deferred Linux environment observation for V1.1 preload admission."""
from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from importlib.metadata import version

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    PACKAGE_IDENTITIES,
    GenerationPreloadObservationV1_1,
)

NVIDIA_SMI_COMMAND = (
    "nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,compute_cap",
    "--format=csv,noheader,nounits",
)


def observe_linux_generation_preload_v1_1(
    *, base_manifest_sha256: str, adapter_manifest_sha256: str,
    run_command: Callable[[Sequence[str]], str] | None = None,
    package_version: Callable[[str], str] | None = None,
) -> GenerationPreloadObservationV1_1:
    """Observe exact packages/GPU only when explicitly called at runtime."""
    runner = run_command or _run_command
    versions = package_version or version
    if not callable(runner) or not callable(versions):
        raise TypeError("GENERATION_PRELOAD_V1_1_OBSERVER_CALLABLES_REQUIRED")
    observed_packages = tuple(
        f"{identity.split('==', 1)[0]}=={versions(identity.split('==', 1)[0])}"
        for identity in PACKAGE_IDENTITIES
    )
    raw = runner(NVIDIA_SMI_COMMAND)
    if type(raw) is not str:
        raise TypeError("GENERATION_PRELOAD_V1_1_NVIDIA_SMI_TEXT_REQUIRED")
    rows = [row.strip() for row in raw.splitlines() if row.strip()]
    if len(rows) != 1:
        raise ValueError("GENERATION_PRELOAD_V1_1_EXACTLY_ONE_GPU_REQUIRED")
    columns = tuple(item.strip() for item in rows[0].split(","))
    if len(columns) != 5:
        raise ValueError("GENERATION_PRELOAD_V1_1_GPU_OBSERVATION_SHAPE_INVALID")
    try:
        index, total, free = int(columns[0]), int(columns[2]), int(columns[3])
    except ValueError as exc:
        raise ValueError("GENERATION_PRELOAD_V1_1_GPU_OBSERVATION_VALUE_INVALID") from exc
    return GenerationPreloadObservationV1_1(
        observed_packages, base_manifest_sha256, adapter_manifest_sha256,
        columns[1], total, free, columns[4], index, "NF4_4BIT", True, "BF16")


def _run_command(command: Sequence[str]) -> str:
    completed = subprocess.run(
        tuple(command), check=True, capture_output=True, text=True, timeout=10.0)
    if completed.stderr.strip():
        raise RuntimeError("GENERATION_PRELOAD_V1_1_NVIDIA_SMI_STDERR_NONEMPTY")
    return completed.stdout


__all__ = (
    "NVIDIA_SMI_COMMAND", "observe_linux_generation_preload_v1_1",
)
