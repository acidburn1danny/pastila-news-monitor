"""Launch-forbidden static executor binding for Construction-Obligation V2."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import (
    CONTRACT_IDENTITY as HOST_PAYLOAD_CONTRACT_IDENTITY,
    ConstructionObligationV2HostWslPayloadV1,
    parse_construction_obligation_v2_host_wsl_payload_v1,
)


FEASIBILITY_DESIGN_IDENTITY = "31a82ff316f69f98f7ba5df0e53bf5c6262fad5068fb3580430b967e5930658f"
STATIC_BINDING_IDENTITY = "46265e64cfac4217493529020f7517d6af1f10d93f14a3fed2abd2cc6e8c4572"
MODEL_IDENTITY = "pastila-editor-core-v1.2-experimental"
SYSTEM_PROMPT_IDENTITY = "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2"
SYSTEM_PROMPT_SHA256 = "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"
BASE_MODEL_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142"
ADAPTER_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-2-deontology-20260820-003/checkpoint-final/adapter"
CANONICAL_WSL_PROFILE_IDENTITY = "89d41dda4fbc1999e8aaf8f6ec62eabbdb7672535303337d37d3eb8c168d4afd"

_DEPENDENCIES = {
    Path("src/pastila_scout/experimental_core_v1_2.py"):
        "8fe9e740b3263f2988a653a0343334b502fddf0d3cb2be36746de4646242bed5",
    Path("src/pastila_scout/experimental_core_v1_2_runner.py"):
        "51c7ff37731c5f4a9cacda7ee3a9d1966e51bb80098ce2ea6503a34345ee06a9",
    Path("src/pastila_scout/wsl_execution_v1/boundary.py"):
        "089274ad1d9eb3f0db1891c5be65a97a6fd71f9fac5bdd32cf5c07dd5a2833ca",
    Path("src/pastila_scout/wsl_execution_v1_1/boundary.py"):
        "87ef25d65a92b65e8dbd3730258c6d0b0fc6ee8950130c69e2b623ff0190127e",
    Path(".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"):
        SYSTEM_PROMPT_SHA256,
}


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2StaticExecutorBindingV1:
    binding_identity: str
    static_binding_identity: str
    host_payload_contract_identity: str
    host_payload_identity: str
    host_payload_sha256: str
    provider_request_id: str
    source_context_identity: str
    model_identity: str
    system_prompt_identity: str
    system_prompt_sha256: str
    base_model_path: str
    adapter_path: str
    wsl_profile_identity: str
    max_output_tokens: int
    _wsl_boundary: WslExecutionBoundaryV1_1 = field(repr=False, compare=False)


def bind_construction_obligation_v2_static_executor_v1(
    *, project_root: Path, raw_host_payload: bytes,
    wsl_boundary: WslExecutionBoundaryV1_1,
) -> ConstructionObligationV2StaticExecutorBindingV1:
    """Bind identities and an inert transport capability without invoking it."""
    if not isinstance(project_root, Path):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_PROJECT_ROOT_PATH_REQUIRED")
    root = project_root.resolve(strict=True)
    if type(wsl_boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_WSL_BOUNDARY_V1_1_EXACT_TYPE_REQUIRED")
    expected_profile = canonical_model_profile_v1()
    if (
        wsl_boundary.profile != expected_profile
        or wsl_boundary.profile.identity != CANONICAL_WSL_PROFILE_IDENTITY
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_WSL_PROFILE_IDENTITY_MISMATCH")
    for relative, expected_sha256 in _DEPENDENCIES.items():
        target = root / relative
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
            raise RuntimeError(
                f"CONSTRUCTION_OBLIGATION_V2_STATIC_EXECUTOR_DEPENDENCY_DRIFT:{relative.as_posix()}"
            )
    payload = parse_construction_obligation_v2_host_wsl_payload_v1(
        raw_payload=raw_host_payload)
    raw_sha256 = hashlib.sha256(raw_host_payload).hexdigest()
    binding_identity = _binding_identity(payload, raw_sha256)
    return ConstructionObligationV2StaticExecutorBindingV1(
        binding_identity, STATIC_BINDING_IDENTITY, HOST_PAYLOAD_CONTRACT_IDENTITY,
        payload.payload_identity, raw_sha256, payload.provider_request_id,
        payload.source_context_identity, MODEL_IDENTITY, SYSTEM_PROMPT_IDENTITY,
        SYSTEM_PROMPT_SHA256, BASE_MODEL_PATH, ADAPTER_PATH,
        CANONICAL_WSL_PROFILE_IDENTITY, payload.max_output_tokens, wsl_boundary,
    )


def _binding_identity(
    payload: ConstructionObligationV2HostWslPayloadV1, raw_sha256: str,
) -> str:
    fields = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_STATIC_EXECUTOR_BINDING_INSTANCE_V1",
        STATIC_BINDING_IDENTITY, HOST_PAYLOAD_CONTRACT_IDENTITY,
        payload.payload_identity, raw_sha256, payload.provider_request_id,
        payload.source_context_identity, MODEL_IDENTITY, SYSTEM_PROMPT_SHA256,
        BASE_MODEL_PATH, ADAPTER_PATH, CANONICAL_WSL_PROFILE_IDENTITY,
        str(payload.max_output_tokens), "LAUNCH_FORBIDDEN",
    )
    return hashlib.sha256("\n".join(fields).encode()).hexdigest()


__all__ = (
    "STATIC_BINDING_IDENTITY", "ConstructionObligationV2StaticExecutorBindingV1",
    "bind_construction_obligation_v2_static_executor_v1",
)
