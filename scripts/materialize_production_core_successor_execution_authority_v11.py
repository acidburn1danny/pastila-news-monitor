"""Build and detached-sign the zero-attempt V11 execution authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = "29616718e9d17a3c88f630af52fee0ef7a9dc7adc519412c4870f06b63ca1cca"
SOURCES = (
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/execute_production_core_candidate_qualification_v11.py",
    "scripts/launch_production_core_candidate_qualification_v11.py",
    "scripts/preflight_production_core_wsl_host_capacity_v11.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v11.sh",
    "scripts/smoke_production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v11.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
)
IDS = {
    "qualification_generation_identity": "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7",
    "qualification_identity": "607ef6193b312c6d2e5d581c10caf9cb8a3a14a5b46166888e9bd8bddade5a45",
    "request_manifest_identity": "f3b0e0d11c5b73fba39ce21f5daa040e788a2ea09d455389bf990ee8264b4d03",
    "candidate_object_manifest_identity": "6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314",
    "candidate_audit_receipt_identity": "50eb1fb7b425fdee07b7fbd672c405c0dc2cd5b34e0df6270bb0468c3ea846d8",
    "execution_contract_sha256": "eb2ab0914175f0f9ae50882c4c96fbc792cfee1fe40fa39740b9ef8f58a1825d",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def committed_source(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, check=False, capture_output=True
    )
    if result.returncode != 0:
        raise ValueError(f"source absent from bound commit: {path}")
    raw = result.stdout
    if raw != (ROOT / path).read_bytes():
        raise ValueError(f"worktree differs from bound commit: {path}")
    return raw


def build(commit: str):
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("full lowercase source commit required")
    sources = {path: hashlib.sha256(committed_source(commit, path)).hexdigest() for path in SOURCES}
    core = {
        "schema": "pastila-production-core-candidate-execution-authority",
        "schema_version": 12,
        "status": "FROZEN_SUCCESSOR_V11_WSL_SIGBUS_REMEDIATION_ZERO_ATTEMPTS",
        "bound_source_commit": commit,
        "predecessor_terminal_disposition_identity": "6550b88c424adda261fa723c08f3ce128d61cbdc811cb4d2b311657dc9f04983",
        "authority_identities": IDS,
        "source_sha256": sources,
        "matrix_rows": 2400,
        "checkpoint_policy": {"checkpoint_count": 12, "rows_per_checkpoint": 200, "ordinal_source": "VALIDATED_AUTHORITY_SCHEDULE", "atomic_publish": True, "content_addressed_receipt": True, "same_attempt_resume_only": True, "recalculate_finalized_rows": False},
        "lifecycle_completed_contract": {"termination_reason_required": True, "termination_reason_observation_binding_required": True, "missing_wrong_or_extra_fields_rejected": True},
        "attempt_ordinal": 1,
        "attempt_consumption_authorized": False,
        "candidate_execution_authorized": False,
        "retry_or_redraw_authorized": False,
        "adjudication_performed": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    return {**core, "execution_authority_identity": hashlib.sha256(canonical(core)).hexdigest()}


def put(path: Path, raw: bytes):
    if path.exists() and (path.is_symlink() or path.read_bytes() != raw):
        raise SystemExit(f"published artifact differs: {path}")
    if not path.exists():
        path.write_bytes(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bound-source-commit", required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--openssl", type=Path, required=True)
    options = parser.parse_args()
    authority = build(options.bound_source_commit)
    raw = json.dumps(authority, ensure_ascii=False, indent=2).encode() + b"\n"
    put(options.authority, raw)
    binding = {"schema": "pastila-production-core-v11-detached-authority-binding", "schema_version": 1, "algorithm": "Ed25519", "public_key_sha256": PUB, "authority_identity": authority["execution_authority_identity"], "authority_sha256": hashlib.sha256(raw).hexdigest(), "bound_source_commit": options.bound_source_commit, "source_sha256": authority["source_sha256"], "candidate_execution_authorized": False, "attempt_consumption_authorized": False}
    binding_raw = canonical(binding)
    put(options.binding, binding_raw)
    if not options.signature.exists():
        subprocess.run([str(options.openssl), "pkeyutl", "-sign", "-inkey", str(options.private_key), "-rawin", "-in", str(options.binding), "-out", str(options.signature)], check=True)
    if options.signature.is_symlink() or len(options.signature.read_bytes()) != 64:
        raise SystemExit("signature malformed")
    print(json.dumps({"authority_identity": authority["execution_authority_identity"], "binding_sha256": hashlib.sha256(binding_raw).hexdigest(), "signature_sha256": hashlib.sha256(options.signature.read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
