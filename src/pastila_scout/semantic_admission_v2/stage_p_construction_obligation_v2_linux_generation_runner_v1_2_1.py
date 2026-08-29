"""Five-path Linux entrypoint for the V1.2.1 source binding."""
from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from .stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1 import LINUX_GENERATION_COMPOSITION_IDENTITY, LinuxGenerationCompositionOutcomeV1_2, run_linux_generation_composition_v1_2_1

CANONICAL_DURABLE_SINK_SOURCE_SHA256 = "fb5caa812f13fd2c2591396de3d6a38eddba7187c5e35bc08e0b713c6e7658db"
CANONICAL_COMPOSITION_SOURCE_SHA256 = "af70ec8e19aa07c7521053ad6cb233935d2f1342e63a18cc6af5da256a697b81"
CANONICAL_RUNTIME_ADAPTER_SOURCE_SHA256 = "8e3499105980a730339941252ffd47466cc9eb39a0dc50d59220b6f1dd666dde"
CANONICAL_EXACT_OPERATIONS_ADAPTER_SOURCE_SHA256 = "49df5740ead01e982e3cae49dfcef5e71c8aab4ccca33d2de06720665116fa3e"
CANONICAL_WORKER_SOURCE_SHA256 = "5c310e144687bd1b4ff340b5ced0c4976a0f1cc9c4205ed67cd1e808b7f75c9f"
CANONICAL_INJECTED_SUPERVISOR_SOURCE_SHA256 = "95b7b0466727779740164268f4b09758d68a685e27855cd95310e7fa48fa2f24"
CANONICAL_SUPERVISOR_CANDIDATE_SOURCE_SHA256 = "21e6d70f50d5cc8f6663fbb4851f980e7c09ff4ce23bc2ee72768d81fb8dccb9"
CANONICAL_CHILD_ADAPTER_SOURCE_SHA256 = "71d212385c1dbac6285013f5f9bc61f34ce031514f616baa84796d9c2491e275"
LINUX_GENERATION_RUNNER_IDENTITY_FIELDS = (
    "construction-obligation-v2-linux-generation-runner-v1.2.1",
    "five-canonical-paths",
    "composition:" + LINUX_GENERATION_COMPOSITION_IDENTITY,
    "durable-sink-source:" + CANONICAL_DURABLE_SINK_SOURCE_SHA256,
    "composition-source:" + CANONICAL_COMPOSITION_SOURCE_SHA256,
    "runtime-adapter-source:" + CANONICAL_RUNTIME_ADAPTER_SOURCE_SHA256,
    "exact-operations-adapter-source:" + CANONICAL_EXACT_OPERATIONS_ADAPTER_SOURCE_SHA256,
    "worker-source:" + CANONICAL_WORKER_SOURCE_SHA256,
    "injected-supervisor-source:" + CANONICAL_INJECTED_SUPERVISOR_SOURCE_SHA256,
    "supervisor-candidate-source:" + CANONICAL_SUPERVISOR_CANDIDATE_SOURCE_SHA256,
    "child-adapter-source:" + CANONICAL_CHILD_ADAPTER_SOURCE_SHA256,
    "inner-timeout:1200",
)
LINUX_GENERATION_RUNNER_IDENTITY = hashlib.sha256(
    "\n".join(LINUX_GENERATION_RUNNER_IDENTITY_FIELDS).encode()
).hexdigest()
SYSTEM_PROMPT_SHA256 = "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"
INNER_TIMEOUT_SECONDS = 1200.0


def run_linux_generation_runner_v1_2_1(
    *, policy_receipt_path: Path, authority_receipt_path: Path,
    runner_request_path: Path, system_prompt_path: Path, evidence_root: Path,
    composition: Callable[..., LinuxGenerationCompositionOutcomeV1_2] = run_linux_generation_composition_v1_2_1,
) -> LinuxGenerationCompositionOutcomeV1_2:
    if not callable(composition):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_COMPOSITION_REQUIRED")
    policy = _input(policy_receipt_path, "POLICY_RECEIPT", 100_000)
    authority = _input(authority_receipt_path, "AUTHORITY_RECEIPT", 100_000)
    request = _input(runner_request_path, "RUNNER_REQUEST", 600_000)
    prompt_path = _input(system_prompt_path, "SYSTEM_PROMPT", 1_000_000)
    root = _new_root(evidence_root)
    prompt = prompt_path.read_text("utf-8", errors="strict")
    if hashlib.sha256(prompt.encode()).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    outcome = composition(
        raw_policy_receipt=policy.read_bytes(),
        raw_authority_receipt=authority.read_bytes(),
        raw_runner_request=request.read_bytes(),
        system_prompt=prompt, evidence_root=root,
        timeout_seconds=INNER_TIMEOUT_SECONDS,
    )
    if type(outcome) is not LinuxGenerationCompositionOutcomeV1_2:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_V1_2_OUTCOME_EXACT_TYPE_REQUIRED")
    return outcome


def main(arguments: Sequence[str]) -> int:
    if len(arguments) != 5 or any(type(item) is not str or not item for item in arguments):
        raise SystemExit("usage: runner POLICY AUTHORITY RUNNER_REQUEST SYSTEM_PROMPT EVIDENCE_ROOT")
    run_linux_generation_runner_v1_2_1(
        policy_receipt_path=Path(arguments[0]), authority_receipt_path=Path(arguments[1]),
        runner_request_path=Path(arguments[2]), system_prompt_path=Path(arguments[3]),
        evidence_root=Path(arguments[4]),
    )
    return 0


def _input(path: Path, label: str, maximum: int) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_ABSOLUTE_PATH_REQUIRED")
    resolved = path.resolve(strict=True)
    if resolved != path or not resolved.is_file():
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_CANONICAL_FILE_REQUIRED")
    if not 0 < resolved.stat().st_size <= maximum:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_SIZE_INVALID")
    return resolved


def _new_root(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_ROOT_ABSOLUTE_PATH_REQUIRED")
    if path.exists() or path.is_symlink():
        raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_ROOT_ALREADY_EXISTS")
    if path.parent.resolve(strict=True) != path.parent or not path.parent.is_dir():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_PARENT_INVALID")
    return path


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = (
    "INNER_TIMEOUT_SECONDS", "LINUX_GENERATION_RUNNER_IDENTITY",
    "LINUX_GENERATION_RUNNER_IDENTITY_FIELDS", "main",
    "run_linux_generation_runner_v1_2_1",
)
