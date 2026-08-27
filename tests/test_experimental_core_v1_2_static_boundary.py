from __future__ import annotations

import hashlib
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import (
    MODEL_ID,
    SYSTEM_PROMPT_SHA256,
    ExperimentalCoreV12Executor,
    load_frozen_system_prompt,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_prompt_is_git_resident_and_identity_exact() -> None:
    prompt = load_frozen_system_prompt(project_root=ROOT)
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == SYSTEM_PROMPT_SHA256
    assert MODEL_ID == "pastila-editor-core-v1.2-experimental"


def test_executor_construction_binds_canonical_transport_without_launch() -> None:
    executor = ExperimentalCoreV12Executor(project_root=ROOT, max_output_tokens=64)
    assert type(executor._wsl_boundary) is WslExecutionBoundaryV1_1
    assert executor._max_output_tokens == 64
