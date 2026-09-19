"""Restore and verify the effective V15 namespace after the pinned V3 projection.

R3's second compilation of the V3 mechanics resets module globals. This
successor restores only the frozen V14/V15 execution inputs, then checks the
namespace that the consuming ``main`` will actually use.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import project_production_core_candidate_qualification_v15_r3 as r3
from pastila_scout import production_core_successor_contract_v15_r3 as contract

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "scripts/project_production_core_candidate_qualification_v15_r4.py"


def expected_bindings() -> dict:
    v15 = r3.predecessor
    v14 = v15.predecessor
    return {
        "ROOT": ROOT,
        "ART": ROOT / "docs/artifacts",
        "HELPER": ROOT / "scripts/resolve_production_core_object_authority_v2.sh",
        "NAMES": v14.NAMES,
        "RUNNER": v15.RUNNER,
        "LAUNCHER": v15.LAUNCHER,
        "PROMPTS": v14.PROMPTS,
        "PROMPT_SHA256": v14.PROMPT_SHA256,
        "SNAPSHOT": v15.SNAPSHOT,
        "DRIVER_HELPER": v15.DRIVER_HELPER,
        "object_authority": v14.object_authority,
        "wsl": v14.linux_path,
        "lock_directory": v15.lock_directory,
        "atomic": v15.atomic_no_replace,
        "validate_manifest_contract": contract.validate_manifest_contract,
        "case_for_row": contract.case_for_row,
        "close_post_claim_failure": contract.close_post_claim_failure,
    }


def binding_claim(source_sha256: dict[str, str]) -> dict:
    """Portable claim for every mutable execution global restored here."""
    return {
        "snapshot_set": list(expected_bindings()["NAMES"]),
        "launcher_path": "scripts/run_production_core_candidate_qualification_v15.sh",
        "launcher_sha256": source_sha256["scripts/run_production_core_candidate_qualification_v15.sh"],
        "runner_path": "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
        "runner_sha256": source_sha256["src/pastila_scout/production_core_candidate_qualification_runner_v14.py"],
        "prompt_sha256": dict(expected_bindings()["PROMPT_SHA256"]),
        "lock_source_sha256": source_sha256["scripts/execute_production_core_candidate_qualification_v15.py"],
        "atomic_source_sha256": source_sha256["scripts/execute_production_core_candidate_qualification_v15.py"],
        "driver_snapshot_path": str(expected_bindings()["SNAPSHOT"]),
        "driver_helper_sha256": source_sha256["src/pastila_scout/production_core_wsl_driver_snapshot_v15.py"],
        "qualification_generation_identity": r3.predecessor.validator.GENERATION_IDENTITY,
        "qualification_identity": r3.predecessor.validator.QUALIFICATION_IDENTITY,
        "matrix_rows": r3.predecessor.validator.MATRIX_ROWS,
    }


def verify_namespace(namespace: dict, boundary: dict) -> None:
    """Check the live globals used by main before any attempt can be claimed."""
    sources = boundary.get("source_sha256")
    if not isinstance(sources, dict) or not isinstance(namespace, dict):
        raise ValueError("R4 executable source authority absent")
    for name in (SOURCE, *r3.SOURCE_PATHS):
        path = ROOT / name
        if (path.is_symlink() or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != sources.get(name)):
            raise ValueError(f"R4 executable source drift: {name}")
    for key, expected in expected_bindings().items():
        observed = namespace.get(key)
        if (type(observed) is not type(expected)
                or (observed is not expected if callable(expected) else observed != expected)):
            raise ValueError(f"R4 executable namespace mismatch: {key}")
    v15 = r3.predecessor
    if (namespace.get("PINNED_ENTRY_EXECUTOR_SHA256") !=
            sources.get("scripts/execute_production_core_candidate_qualification_v15.py")
            or namespace.get("PINNED_ROOTFS_SHA256") !=
            v15.validator.EXPECTED_OBJECTS[0][2]
            or namespace.get("PINNED_UNICODE_AUTHORITY_SHA256") !=
            v15.validator.UNICODE_AUTHORITY_SHA256
            or namespace.get("GENERATION_IDENTITY") != v15.validator.GENERATION_IDENTITY
            or namespace.get("QUALIFICATION_IDENTITY") != v15.validator.QUALIFICATION_IDENTITY
            or namespace.get("MATRIX_ROWS") != v15.validator.MATRIX_ROWS
            or namespace.get("PINNED_TERMINAL_VALIDATOR") is not
            v15.predecessor.terminal_validator
            or namespace.get("validate_preflight") is not
            v15.predecessor.validate_and_map
            or namespace.get("validate_response_v2") is not v15.semantic.validate_response_v2
            or namespace.get("object_authority") is not v15.predecessor.object_authority
            or namespace.get("wsl") is not v15.predecessor.linux_path):
        raise ValueError("R4 inherited executable namespace mismatch")
    mechanism = namespace.get("PINNED_EXECUTION_MECHANISM")
    expected_mechanism = v15.build_namespace(boundary)["PINNED_EXECUTION_MECHANISM"]
    if (not isinstance(mechanism, dict)
            or mechanism != expected_mechanism
            or mechanism.get("execution_authority_identity") != boundary.get("boundary_identity")):
        raise ValueError("R4 executable mechanism mismatch")
    if not callable(namespace.get("main")) or not callable(namespace.get("atomic")):
        raise ValueError("R4 executable entry missing")


def build_namespace(boundary: dict) -> dict:
    sources = boundary.get("source_sha256")
    if not isinstance(sources, dict):
        raise ValueError("R4 source authority absent")
    path = ROOT / SOURCE
    if (path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != sources.get(SOURCE)):
        raise ValueError("R4 projection source drift")
    namespace = r3.build_namespace(boundary)
    namespace.update(expected_bindings())
    verify_namespace(namespace, boundary)
    return namespace
