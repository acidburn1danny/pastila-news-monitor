"""Linux module entrypoint for the frozen V2 generation composition.

Importing this module is inert. Calling ``run_linux_generation_runner_v1`` is
the explicit filesystem/process/model/generation authority boundary.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from .stage_p_construction_obligation_v2_linux_generation_composition_v1 import (
    LinuxGenerationCompositionOutcomeV1,
    run_linux_generation_composition_v1,
)

LINUX_GENERATION_RUNNER_IDENTITY = (
    "ed9303593dea53b9375913e3cb1640cdb11f2e347299435532f7e3935bf755da"
)
SYSTEM_PROMPT_SHA256 = (
    "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"
)
INNER_TIMEOUT_SECONDS = 1200.0


def run_linux_generation_runner_v1(
    *,
    policy_receipt_path: Path,
    authority_receipt_path: Path,
    runner_request_path: Path,
    system_prompt_path: Path,
    evidence_root: Path,
    composition: Callable[..., LinuxGenerationCompositionOutcomeV1] = (
        run_linux_generation_composition_v1
    ),
) -> LinuxGenerationCompositionOutcomeV1:
    """Read five exact paths, then cross the composition authority boundary."""
    if not callable(composition):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_COMPOSITION_REQUIRED")
    policy_path = _input(policy_receipt_path, "POLICY_RECEIPT", 100_000)
    authority_path = _input(authority_receipt_path, "AUTHORITY_RECEIPT", 100_000)
    request_path = _input(runner_request_path, "RUNNER_REQUEST", 600_000)
    prompt_path = _input(system_prompt_path, "SYSTEM_PROMPT", 1_000_000)
    root = _new_root(evidence_root)
    prompt = prompt_path.read_text("utf-8", errors="strict")
    if hashlib.sha256(prompt.encode("utf-8")).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    outcome = composition(
        raw_policy_receipt=policy_path.read_bytes(),
        raw_authority_receipt=authority_path.read_bytes(),
        raw_runner_request=request_path.read_bytes(),
        system_prompt=prompt,
        evidence_root=root,
        timeout_seconds=INNER_TIMEOUT_SECONDS,
    )
    if type(outcome) is not LinuxGenerationCompositionOutcomeV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_OUTCOME_EXACT_TYPE_REQUIRED")
    return outcome


def main(arguments: Sequence[str]) -> int:
    if len(arguments) != 5 or any(
        type(item) is not str or not item for item in arguments
    ):
        raise SystemExit(
            "usage: runner POLICY AUTHORITY RUNNER_REQUEST SYSTEM_PROMPT EVIDENCE_ROOT"
        )
    run_linux_generation_runner_v1(
        policy_receipt_path=Path(arguments[0]),
        authority_receipt_path=Path(arguments[1]),
        runner_request_path=Path(arguments[2]),
        system_prompt_path=Path(arguments[3]),
        evidence_root=Path(arguments[4]),
    )
    # A reconciled typed EXECUTION_FAILURE is a successful transport. Its
    # classification lives in durable receipts and must not become WSL failure.
    return 0


def _input(path: Path, label: str, maximum: int) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_ABSOLUTE_PATH_REQUIRED")
    resolved = path.resolve(strict=True)
    if resolved != path or not resolved.is_file():
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_CANONICAL_FILE_REQUIRED")
    size = resolved.stat().st_size
    if not 0 < size <= maximum:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_SIZE_INVALID")
    return resolved


def _new_root(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(
            "CONSTRUCTION_OBLIGATION_V2_EVIDENCE_ROOT_ABSOLUTE_PATH_REQUIRED"
        )
    if path.exists() or path.is_symlink():
        raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_ROOT_ALREADY_EXISTS")
    if path.parent.resolve(strict=True) != path.parent or not path.parent.is_dir():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_PARENT_INVALID")
    return path


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = (
    "INNER_TIMEOUT_SECONDS",
    "LINUX_GENERATION_RUNNER_IDENTITY",
    "SYSTEM_PROMPT_SHA256",
    "main",
    "run_linux_generation_runner_v1",
)
