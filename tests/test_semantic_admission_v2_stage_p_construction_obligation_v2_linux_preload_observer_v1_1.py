from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_preload_observer_v1_1 import (
    NVIDIA_SMI_COMMAND,
    observe_linux_generation_preload_v1_1,
)

BASE = "1" * 64
ADAPTER = "2" * 64
VERSIONS = {
    "transformers": "5.15.0", "torch": "2.13.0+cu130", "peft": "0.20.0",
    "accelerate": "1.14.0", "bitsandbytes": "0.50.1",
}


def test_exact_observation_is_deferred_and_parsed() -> None:
    calls = []

    def run(command):
        calls.append(tuple(command))
        return "0, NVIDIA GeForce RTX 5080, 16303, 15001, 12.0\n"

    observed = observe_linux_generation_preload_v1_1(
        base_manifest_sha256=BASE, adapter_manifest_sha256=ADAPTER,
        run_command=run, package_version=VERSIONS.__getitem__)
    assert calls == [NVIDIA_SMI_COMMAND]
    assert observed.vram_free_mib == 15001 and observed.cuda_device == 0
    assert observed.package_identities[1] == "torch==2.13.0+cu130"


@pytest.mark.parametrize("raw", ["", "0, bad\n", "0, GPU, x, 15000, 12.0\n",
                                  "0, GPU, 1, 1, 1\n1, GPU, 1, 1, 1\n"])
def test_malformed_or_ambiguous_gpu_observations_fail_closed(raw) -> None:
    with pytest.raises((ValueError, TypeError)):
        observe_linux_generation_preload_v1_1(
            base_manifest_sha256=BASE, adapter_manifest_sha256=ADAPTER,
            run_command=lambda _: raw, package_version=VERSIONS.__getitem__)


def test_import_has_no_command_execution() -> None:
    source = Path(
        "src/pastila_scout/semantic_admission_v2/"
        "stage_p_construction_obligation_v2_linux_preload_observer_v1_1.py"
    ).read_text("utf-8")
    tree = ast.parse(source)
    top_level_calls = [node for node in tree.body if isinstance(node, ast.Expr)
                       and isinstance(node.value, ast.Call)]
    assert top_level_calls == []
