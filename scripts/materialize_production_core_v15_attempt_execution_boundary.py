"""Sign a distinct V15 attempt route without granting consumption."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_successor_execution_authority_v15 as predecessor
import materialize_production_core_successor_execution_authority_v12 as signing
import preflight_production_core_candidate_qualification_v15 as gate
from pastila_scout import production_core_wsl_driver_snapshot_v15 as drivers

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-attempt-execution-boundary"
V15_AUTHORITY = gate.AUTHORITY
V15_BINDING = gate.BINDING
V15_SIGNATURE = gate.SIGNATURE
PREFLIGHT_COMMIT = "6415c3307dcfff4205c6d23af2db4102d933d160"
PREFLIGHT_TREE = "edb8c64fabaa721422a8224e46f284c311de36e1"
PREFLIGHT_RECEIPT = "16f0910b58476058d6d350bd64c28a2f23127d0c9e5dd58c6fe7179aa9c9174d"
SOURCE_FILES = (
    "docs/production-core-v15-attempt-execution-boundary.md",
    "docs/production-core-v15-preconsumption-preflight.md",
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/audit_production_core_v15_attempt_execution_boundary.py",
    "scripts/audit_production_core_v15_preconsumption_preflight.py",
    "scripts/execute_production_core_candidate_qualification_v3.py",
    "scripts/execute_production_core_candidate_qualification_v14.py",
    "scripts/execute_production_core_candidate_qualification_v15.py",
    "scripts/launch_production_core_candidate_qualification_v15.py",
    "scripts/preflight_production_core_candidate_qualification_v15.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v15.sh",
    "scripts/smoke_production_core_checkpoint_resume_v6.py",
    "scripts/smoke_production_core_v15_attempt_execution_boundary.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v14.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v15.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
    "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py",
    "tests/test_production_core_v15_attempt_execution_boundary.py",
    "tests/test_production_core_v15_preconsumption_preflight.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_closure() -> dict[str, str]:
    gate.published_source_closure()
    if gate.git("rev-parse", f"{PREFLIGHT_COMMIT}^{{tree}}") != PREFLIGHT_TREE:
        raise ValueError("published V15 preflight tree mismatch")
    published = gate.git("diff-tree", "--no-commit-id", "--name-only", "-r", PREFLIGHT_COMMIT).splitlines()
    if published != [
        "docs/production-core-v15-preconsumption-preflight.md",
        "scripts/audit_production_core_v15_preconsumption_preflight.py",
        "scripts/preflight_production_core_candidate_qualification_v15.py",
        "tests/test_production_core_v15_preconsumption_preflight.py",
    ]:
        raise ValueError("published V15 preflight file scope mismatch")
    result = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"V15 attempt source missing: {name}")
        raw = path.read_bytes()
        if subprocess.run(["git", "cat-file", "-e", f"{PREFLIGHT_COMMIT}:{name}"],
                          cwd=ROOT, capture_output=True).returncode == 0:
            if raw != subprocess.check_output(["git", "show", f"{PREFLIGHT_COMMIT}:{name}"], cwd=ROOT):
                raise ValueError(f"published V15 attempt source drift: {name}")
        result[name] = digest(raw)
    return result


def build(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, output: Path) -> dict:
    sources = source_closure()
    published = predecessor.audit(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot)
    if any(published.get(key) != value for key, value in {
        "verdict": "PASS + 0 BLOCKERS", "authority_identity": V15_AUTHORITY,
        "binding_identity": V15_BINDING, "signature_identity": V15_SIGNATURE,
        "ed25519_verification": "PASS", "runtime_object_closure": "PASS",
        "driver_snapshot_closure": "PASS", "isolated_cuda": "PASS",
        "new_candidate_execution": "0", "new_attempt_consumption": "0",
    }.items()):
        raise ValueError("published V15 execution authority rejected")
    v15 = json.loads((ROOT / "docs/artifacts/production-core-v15-successor-execution-authority/authority.json").read_bytes())
    driver = drivers.manifest(snapshot)
    if driver != v15["driver_snapshot"]:
        raise ValueError("V15 ext4 driver snapshot drift")
    output_state = gate.empty_output(output, (ROOT, recovery, private, backup, v13_terminal,
                                              terminal, rootfs, snapshot))
    if (output_state["path"] != "/root/pf9-v15-preconsumption-output"
            or output_state["entries"] != 0):
        raise ValueError("V15 real output binding mismatch")
    import execute_production_core_candidate_qualification_v15 as executor
    from pastila_scout import production_core_candidate_execution_authority_v15 as validator

    projection = executor.projected_mechanics()
    if (projection.count("            str(SNAPSHOT),\n") != 1
            or projection.count("            str(DRIVER_HELPER),\n") != 1
            or projection.count("            hashlib.sha256(read(DRIVER_HELPER)).hexdigest(),\n") != 1
            or "scripts/run_production_core_candidate_qualification_v14.sh" in projection
            or validator.GENERATION_IDENTITY != v15["qualification_generation_identity"]
            or validator.QUALIFICATION_IDENTITY != v15["qualification_identity"]):
        raise ValueError("V15 executor projection or qualification mismatch")
    if source_closure() != sources or drivers.manifest(snapshot) != driver:
        raise ValueError("V15 source or driver changed during attempt binding")
    core = {
        "schema": "pastila-production-core-v15-attempt-execution-boundary",
        "schema_version": 1, "status": "SIGNED_NO_CANDIDATE_NO_ATTEMPT",
        "published_v15_authority_checkpoint": gate.COMMIT,
        "published_v15_authority_tree": gate.TREE,
        "published_v15_preflight_commit": PREFLIGHT_COMMIT,
        "published_v15_preflight_tree": PREFLIGHT_TREE,
        "v15_authority_identity": V15_AUTHORITY, "v15_binding_identity": V15_BINDING,
        "v15_signature_identity": V15_SIGNATURE,
        "preflight_receipt_identity": PREFLIGHT_RECEIPT,
        "v14_terminal_evidence": v15["predecessor_v14_terminal_evidence"],
        "recovery_resolution_identity": v15["recovery_resolution_identity"],
        "runtime_object_authority_identity": v15["runtime_object_authority_identity"],
        "qualification_generation_identity": v15["qualification_generation_identity"],
        "qualification_identity": v15["qualification_identity"],
        "alias_secret_commitment": v15["alias_secret_commitment"],
        "schedule_sha256": v15["schedule_sha256"],
        "matrix_rows": 2400, "batch_count": 12, "rows_per_batch": 200,
        "runner_sha256": sources["src/pastila_scout/production_core_candidate_qualification_runner_v14.py"],
        "launcher_sha256": sources["scripts/run_production_core_candidate_qualification_v15.sh"],
        "executor_sha256": sources["scripts/execute_production_core_candidate_qualification_v15.py"],
        "validator_sha256": sources["src/pastila_scout/production_core_candidate_execution_authority_v15.py"],
        "preflight_source_sha256": sources["scripts/preflight_production_core_candidate_qualification_v15.py"],
        "rootfs_sha256": v15["rootfs_sha256"], "driver_snapshot": driver,
        "output": output_state,
        "shell_argument_count": 16,
        "attempt_claim": "EXCLUSIVE_DIRECTORY_FLOCK_THEN_DURABLE_NO_CLOBBER_ATTEMPT_JSON_BEFORE_LAUNCHER",
        "candidate_execution_boundary": "FIRST_V15_SHELL_SUBPROCESS_AFTER_DURABLE_ATTEMPT_JSON",
        "resume_policy": "NO_RESTART_OR_REEXECUTION_AFTER_ATTEMPT_JSON",
        "source_sha256": sources, "builder_sha256": digest(Path(__file__).read_bytes()),
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0, "attempt_consumption": 0,
        "candidate_execution_authorized": False, "attempt_consumption_authorized": False,
        "adjudication": False, "promotion": False,
    }
    return {**core, "boundary_identity": digest(canonical(core))}


def binding_for(boundary: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v15-detached-attempt-execution-binding",
        "schema_version": 1, "algorithm": "Ed25519",
        "boundary_identity": boundary["boundary_identity"], "boundary_sha256": digest(raw),
        "v15_authority_identity": V15_AUTHORITY, "v15_binding_identity": V15_BINDING,
        "v15_signature_identity": V15_SIGNATURE,
        "published_v15_preflight_commit": PREFLIGHT_COMMIT,
        "preflight_source_sha256": boundary["preflight_source_sha256"],
        "preflight_receipt_identity": PREFLIGHT_RECEIPT,
        "executor_sha256": boundary["executor_sha256"],
        "validator_sha256": boundary["validator_sha256"],
        "launcher_sha256": boundary["launcher_sha256"],
        "driver_snapshot": boundary["driver_snapshot"], "output": boundary["output"],
        "v14_terminal_failure_identity": boundary["v14_terminal_evidence"]["terminal_failure_identity"],
        "attempt_claim": boundary["attempt_claim"],
        "builder_sha256": boundary["builder_sha256"],
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0, "attempt_consumption": 0,
        "adjudication": False, "promotion": False,
    }


def materialize(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
                terminal: Path, rootfs: Path, snapshot: Path, output: Path,
                private_key: Path) -> dict[str, str]:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("V15 attempt boundary already exists")
    signing.verify_key(private_key)
    boundary = build(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output)
    raw = json.dumps(boundary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding_raw = canonical(binding_for(boundary, raw))
    with tempfile.TemporaryDirectory(prefix=".v15-attempt-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "boundary.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(binding_raw)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private_key),
                        "-rawin", "-in", str(staging / "binding.json"),
                        "-out", str(staging / "binding.sig")], check=True, capture_output=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
                        "-rawin", "-in", str(staging / "binding.json"),
                        "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        signature = (staging / "binding.sig").read_bytes()
        if len(signature) != 64:
            raise ValueError("V15 attempt signature length mismatch")
        result = {"boundary_identity": boundary["boundary_identity"],
                  "binding_identity": digest(binding_raw), "signature_identity": digest(signature)}
        os.replace(staging, OUTPUT)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "output", "private-key"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.recovery, args.private, args.backup, args.v13_terminal,
                                 args.terminal, args.rootfs, args.snapshot, args.output,
                                 args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
