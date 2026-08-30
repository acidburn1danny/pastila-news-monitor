"""Five-path Linux entrypoint for the V1.2.1 source binding."""
from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from .stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1 import LINUX_GENERATION_COMPOSITION_IDENTITY, LinuxGenerationCompositionOutcomeV1_2, run_linux_generation_composition_v1_2_1

CANONICAL_DURABLE_SINK_SOURCE_SHA256 = "575a0450aa4aa2a77b118e97b0c4d122371f77e049f59a8365eca77f787d7a9d"
CANONICAL_COMPOSITION_SOURCE_SHA256 = "2425d2952a2bcfe592bd6eb025fd4a3d225b33102eec82c3983533621172f14c"
CANONICAL_RUNTIME_ADAPTER_SOURCE_SHA256 = "53ee02a9788d76dc2df64cf8f493abd86f8d3721bca751436d87a23fde2d1c67"
CANONICAL_EXACT_OPERATIONS_ADAPTER_SOURCE_SHA256 = "80d8b6124c200e2a1d9a4e30f1553ed67feed2ef77f829a153d7d24841ae8c1e"
CANONICAL_WORKER_SOURCE_SHA256 = "602f056733fd86304d0159ac139759ffc9f5f561562f78b0783e75b054b15e79"
CANONICAL_INJECTED_SUPERVISOR_SOURCE_SHA256 = "26beb6028473610c655669c54c028ede28c1e75d843391967c80443cf46b8ff4"
CANONICAL_SUPERVISOR_CANDIDATE_SOURCE_SHA256 = "8e48b04295f3a35b8de49025a6c4820d8bdc1ad2421dda87058b852c667c27fc"
CANONICAL_CHILD_ADAPTER_SOURCE_SHA256 = "9b3819fe207822c03c7a015705c8d3d112337a0b033e6bb9d650f10b47f0057c"
CANONICAL_OPTIMIZED_PROJECTOR_SOURCE_SHA256 = "d8504846c54bc4a0f9a14684c5fb440a4b66837455fceac331c2f70fbb89deaa"
CANONICAL_GENERATED_SUFFIX_SOURCE_SHA256 = "04ac89ccf747f90fd1cf5c877251d00d926faa9014d9877b0d92367cfd223d46"
CANONICAL_OPTIMIZED_CALLBACK_SOURCE_SHA256 = "0738cfabe67465b502bd09c498f1e62f44dbd17ea4c0f91182584a3ba0de0fbd"
CANONICAL_RUNNER_PROTOCOL_CODEC_SOURCE_SHA256 = "d2cef0965fe2067616f333d1bb7eb8eaea09e69e285115facc9a76814bfa310b"
CANONICAL_TOKENIZER_PIECE_SOURCE_SHA256 = "abda08278e362b520c633a150e10aa98280d25efb952fbf81327bee229d551bf"
CANONICAL_SEMANTIC_COMPLETENESS_SOURCE_SHA256 = "8cb943256cc7c2865ceae0a259d1fcd2993949258da067fcdd15531afbff618b"
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
    "optimized-projector-source:" + CANONICAL_OPTIMIZED_PROJECTOR_SOURCE_SHA256,
    "generated-suffix-source:" + CANONICAL_GENERATED_SUFFIX_SOURCE_SHA256,
    "optimized-callback-source:" + CANONICAL_OPTIMIZED_CALLBACK_SOURCE_SHA256,
    "runner-protocol-codec-source:" + CANONICAL_RUNNER_PROTOCOL_CODEC_SOURCE_SHA256,
    "tokenizer-piece-source:" + CANONICAL_TOKENIZER_PIECE_SOURCE_SHA256,
    "semantic-completeness-source:" + CANONICAL_SEMANTIC_COMPLETENESS_SOURCE_SHA256,
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
