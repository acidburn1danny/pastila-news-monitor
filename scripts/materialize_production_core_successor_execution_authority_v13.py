"""Issue a signed zero-attempt authority for the new V13 alias generation."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_successor_execution_authority_v12 as audit_v12
import audit_production_core_successor_qualification_generation_v13 as audit_generation
import materialize_production_core_successor_execution_authority_v12 as authority_v12
import materialize_production_core_successor_qualification_generation_v13 as generation_v13

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
OUTPUT = ART / "production-core-v13-successor-execution-authority"
V12 = ART / "production-core-v12-successor-execution-authority-r2"
COMMIT = generation_v13.SOURCE_COMMIT
TREE = generation_v13.SOURCE_TREE
RUNNER = authority_v12.RUNNER
RESOLUTION = authority_v12.RESOLUTION
PUBLIC_KEY = authority_v12.PUBLIC_KEY
SOURCE_FILES = (
    "scripts/materialize_production_core_successor_qualification_generation_v13.py",
    "scripts/audit_production_core_successor_qualification_generation_v13.py",
)


def source_closure() -> dict[str, str]:
    if authority_v12.git("rev-parse", f"{COMMIT}^{{tree}}").decode() != TREE:
        raise ValueError("canonical published source tree mismatch")
    head = authority_v12.git("rev-parse", "HEAD").decode()
    remote = authority_v12.git("rev-parse", "refs/remotes/origin/successor/core-v2-v12-runner-binding-remediation").decode()
    if not (authority_v12.ancestor(COMMIT, head) and authority_v12.ancestor(COMMIT, remote)):
        raise ValueError("canonical published source commit missing")
    for name in ("authority.json", "binding.json", "binding.sig", "builder-source.py"):
        path = V12 / name
        if path.is_symlink() or path.read_bytes() != subprocess.check_output(
            ["git", "show", f"{COMMIT}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT
        ):
            raise ValueError(f"V12 recovery authority changed: {name}")
    return {name: authority_v12.digest((ROOT / name).read_bytes()) for name in SOURCE_FILES}


def build(recovery_root: Path, private_root: Path, backup_root: Path) -> dict:
    sources = source_closure()
    generation_report = audit_generation.audit(private_root, backup_root)
    v12_report = audit_v12.audit(V12, recovery_root, recompute=True)
    v12_authority = json.loads((V12 / "authority.json").read_bytes())
    if (v12_report["authority_identity"] != "6df414df46d2c76196a74b7e19baeb5c2cf39123cfdec48c7b859cb46e998d8f"
            or v12_authority["recovery_resolution_identity"] != RESOLUTION
            or v12_authority["runner_v12_identity"] != RUNNER):
        raise ValueError("canonical V12 runtime authority mismatch")
    generation = generation_v13.read_json(generation_v13.GENERATION)
    qualification = generation_v13.read_json(generation_v13.QUALIFICATION)
    candidates = generation_v13.read_json(generation_v13.CANDIDATES)
    runtime = v12_authority["runtime_object_closure"]["objects"]
    expected_adapters = set(candidates["adapter_manifest_sha256"].values())
    for label in ("A", "B"):
        observed = {runtime[label][name]["content_identity"] for name in generation_v13.CANDIDATE_NAMES}
        if observed != expected_adapters or runtime[label]["model"]["content_identity"] != candidates["base_model_manifest_sha256"]:
            raise ValueError("candidate weights or recovered object binding mismatch")
    if (generation["qualification_generation_identity"] != generation_report["qualification_generation_identity"]
            or qualification["qualification_identity"] != generation_report["qualification_identity"]
            or generation["alias_secret_commitment"] != generation_report["alias_secret_commitment"]
            or generation["candidate_execution_performed"] is not False
            or generation["qualification_attempt_consumed"] is not False
            or qualification["candidate_execution_performed"] is not False
            or qualification["qualification_attempt_consumed"] is not False):
        raise ValueError("successor generation execution boundary mismatch")
    core = {
        "schema": "pastila-production-core-successor-execution-authority-v13",
        "schema_version": 1,
        "status": "FROZEN_V13_NEW_ALIAS_SECRET_ZERO_ATTEMPTS",
        "bound_source_commit": COMMIT,
        "bound_source_tree": TREE,
        "runner_v12_identity": RUNNER,
        "recovery_resolution_identity": RESOLUTION,
        "v12_runtime_authority_identity": v12_report["authority_identity"],
        "v12_runtime_authority_binding_identity": v12_report["binding_identity"],
        "v12_runtime_authority_signature_identity": v12_report["signature_identity"],
        "v12_executor_projection_sha256": v12_authority["runtime_object_closure"]["executor_projection_sha256"],
        "alias_secret_commitment": generation["alias_secret_commitment"],
        "qualification_generation_identity": generation["qualification_generation_identity"],
        "qualification_identity": qualification["qualification_identity"],
        "schedule_sha256": authority_v12.digest(generation_v13.canonical(generation["schedule"])),
        "request_manifest_identity": generation["request_manifest_identity"],
        "candidate_object_manifest_identity": generation["candidate_object_manifest_identity"],
        "input_envelope_receipt_identities": generation["input_envelope_receipt_identities"],
        "source_sha256": sources,
        "builder_sha256": authority_v12.digest(Path(__file__).read_bytes()),
        "public_key_pem_sha256": authority_v12.PUBLIC_PEM_SHA256,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
        "candidate_execution_authorized": False,
        "attempt_consumption_authorized": False,
    }
    return {**core, "authority_identity": authority_v12.digest(authority_v12.canonical(core))}


def binding_for(authority: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v13-detached-authority-binding",
        "schema_version": 1,
        "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"],
        "authority_sha256": authority_v12.digest(raw),
        "bound_source_commit": COMMIT,
        "bound_source_tree": TREE,
        "runner_v12_identity": RUNNER,
        "recovery_resolution_identity": RESOLUTION,
        "alias_secret_commitment": authority["alias_secret_commitment"],
        "qualification_generation_identity": authority["qualification_generation_identity"],
        "qualification_identity": authority["qualification_identity"],
        "schedule_sha256": authority["schedule_sha256"],
        "v12_runtime_authority_identity": authority["v12_runtime_authority_identity"],
        "builder_sha256": authority["builder_sha256"],
        "public_key_pem_sha256": authority_v12.PUBLIC_PEM_SHA256,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }


def materialize(recovery_root: Path, private_root: Path, backup_root: Path, private_key: Path, output: Path = OUTPUT) -> dict[str, str]:
    if output.exists() or output.is_symlink():
        raise ValueError("V13 authority output already exists")
    authority_v12.verify_key(private_key)
    authority = build(recovery_root, private_root, backup_root)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding_raw = authority_v12.canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v13-authority-", dir=output.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "authority.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(binding_raw)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin", "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")], check=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(PUBLIC_KEY), "-rawin", "-in", str(staging / "binding.json"), "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        signature = (staging / "binding.sig").read_bytes()
        if len(signature) != 64:
            raise ValueError("Ed25519 signature length mismatch")
        result = {
            "authority_identity": authority["authority_identity"],
            "binding_identity": authority_v12.digest(binding_raw),
            "signature_identity": authority_v12.digest(signature),
        }
        os.replace(staging, output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.recovery_root, args.private_root, args.backup_root, args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
