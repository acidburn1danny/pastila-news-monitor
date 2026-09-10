import copy
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_training_runtime_authority_v1 import build_authority

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-training-runtime-authority-v1.json"


def published_observation():
    return json.loads(ARTIFACT.read_bytes())["observation"]


def test_published_authority_passes_and_is_zero_attempt():
    value = json.loads(ARTIFACT.read_bytes())
    assert build_authority(value["observation"]) == value
    assert value["qualification_attempt_consumed"] is False


@pytest.mark.parametrize(
    ("path", "bad"),
    [
        (("compiler", "path"), "/host/bin/gcc"),
        (("launcher_sha256",), "0" * 64),
        (("trainer_sha256",), "0" * 64),
        (("compiler", "version"), "wrong"),
        (("package_versions_sha256",), "0" * 64),
        (("toolchain_inventory_sha256",), "0" * 64),
        (("python_headers_inside_rootfs",), False),
        (("cuda_headers_inside_rootfs",), False),
        (("ptxas_sha256",), "0" * 64),
        (("libcuda_sha256",), "0" * 64),
        (("triton_version",), "wrong"),
        (("wsl_kernel_release",), "wrong"),
        (("gpu", "uuid"), "wrong"),
        (("toolchain_mount_read_only",), False),
        (("rootfs_mount_read_only",), False),
        (("host_path_fallback",), True),
        (("smoke", "backward_4bit"), False),
        (("smoke", "optimizer_steps"), 0),
        (("smoke", "save_reload"), False),
    ],
)
def test_negative_runtime_authority_regressions(path, bad):
    value = copy.deepcopy(published_observation())
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    with pytest.raises(ValueError, match="observation mismatch"):
        build_authority(value)
