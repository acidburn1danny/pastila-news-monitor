"""Build a signed, zero-consumption V14 successor attempt boundary."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_successor_execution_authority_v13 as audit_v13
import materialize_production_core_successor_execution_authority_v12 as signing
from pastila_scout import production_core_candidate_execution_authority_v13 as validator
from pastila_scout.production_core_candidate_qualification_runner_v14 import (
    EXPECTED_GENERATION,
    EXPECTED_QUALIFICATION,
    verify_successor_identities,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v14-successor-attempt-authority"
SOURCE_COMMIT = "0533f2ada34265d411f100beb441941e210d477a"
SOURCE_TREE = "13ac9ce7ce62d91063b12896ef8b7a21510b703b"
V13_AUTHORITY = "2aaa50283451d5338b15d256becccb1ac7e557f12a677126051a036c368d2804"
PREDECESSOR_ATTEMPT = "28358c61c869659b4af1774eecd5f462bf2e209b0cf19503025438deb367a67e"
PREDECESSOR_FAILURE = "8aa8b23f9cec02aaa8157bd4773e6666e4f16ac4987135791655d0c63650ce7d"
SOURCE_FILES = (
    "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
    "scripts/run_production_core_candidate_qualification_v14.sh",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_closure() -> dict[str, str]:
    if signing.git("rev-parse", f"{SOURCE_COMMIT}^{{tree}}").decode() != SOURCE_TREE:
        raise ValueError("published predecessor tree mismatch")
    head = signing.git("rev-parse", "HEAD").decode()
    remote = signing.git("rev-parse", "refs/remotes/origin/successor/core-v2-v12-runner-binding-remediation").decode()
    if not (signing.ancestor(SOURCE_COMMIT, head) and signing.ancestor(SOURCE_COMMIT, remote)):
        raise ValueError("published predecessor source missing")
    for name in ("authority.json", "binding.json", "binding.sig", "builder-source.py"):
        path = ROOT / "docs/artifacts/production-core-v13-successor-execution-authority" / name
        if path.is_symlink() or path.read_bytes() != subprocess.check_output(
            ["git", "show", f"{SOURCE_COMMIT}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT
        ):
            raise ValueError("historical V13 authority drift")
    hashes = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"successor source missing: {name}")
        hashes[name] = digest(path.read_bytes())
    return hashes


def terminal_evidence(root: Path) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("terminal evidence root rejected")
    if {p.name for p in root.iterdir()} != {
        "attempt.json", "terminal-failure.json", "materialization-A", ".checkpoint-01.in-progress"
    }:
        raise ValueError("terminal evidence entry closure mismatch")
    files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix())
    if any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("terminal evidence symlink substitution")
    attempt_path = root / "attempt.json"
    failure_path = root / "terminal-failure.json"
    attempt_raw, failure_raw = attempt_path.read_bytes(), failure_path.read_bytes()
    attempt, failure = json.loads(attempt_raw), json.loads(failure_raw)
    validator.validate_attempt(attempt, V13_AUTHORITY)
    partial = [
        {"path": p.relative_to(root).as_posix(), "sha256": digest(p.read_bytes())}
        for p in files if p != failure_path
    ]
    validator.validate_terminal_failure(failure, attempt, partial)
    if (attempt.get("attempt_identity") != PREDECESSOR_ATTEMPT
            or attempt.get("attempt_ordinal") != 1
            or attempt.get("status") != "CONSUMED_BEFORE_EXECUTION"
            or attempt.get("matrix_rows") != 2400
            or failure.get("terminal_failure_identity") != PREDECESSOR_FAILURE
            or failure.get("completed_rows") != 0
            or failure.get("failure_class") != "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
            or failure.get("failed_batch") != {"materialization": "A", "repetition": 1, "candidate_alias": "CANDIDATE-A"}
            or (root / "completion.json").exists()
            or list(root.glob("checkpoint-*.json"))):
        raise ValueError("predecessor terminal state mismatch")
    return {
        "attempt_identity": PREDECESSOR_ATTEMPT,
        "attempt_sha256": digest(attempt_raw),
        "terminal_failure_identity": PREDECESSOR_FAILURE,
        "terminal_failure_sha256": digest(failure_raw),
        "partial_artifact_root": failure["partial_artifact_root"],
        "completed_rows": 0,
        "accepted_checkpoints": 0,
    }


def runner_binding() -> dict[str, object]:
    verify_successor_identities(EXPECTED_GENERATION, EXPECTED_QUALIFICATION)
    for generation, qualification in (
        ("a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7", EXPECTED_QUALIFICATION),
        (EXPECTED_GENERATION, "607ef6193b312c6d2e5d581c10caf9cb8a3a14a5b46166888e9bd8bddade5a45"),
        ("0" * 64, EXPECTED_QUALIFICATION),
        (EXPECTED_GENERATION, "0" * 64),
    ):
        try:
            verify_successor_identities(generation, qualification)
        except SystemExit:
            pass
        else:
            raise ValueError("stale or substituted runner identity accepted")
    runner = (ROOT / SOURCE_FILES[0]).read_text(encoding="utf-8")
    shell = (ROOT / SOURCE_FILES[1]).read_text(encoding="utf-8")
    if ("QUALIFICATION_IDENTITY=\"$QUALIFICATION_ID\"" not in shell
            or "QUALIFICATION_GENERATION_IDENTITY=\"$GENERATION_ID\"" not in shell
            or "QUALIFICATION_IDENTITY" not in runner
            or "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7" in runner):
        raise ValueError("runner transport or stale source binding mismatch")
    return {
        "qualification_generation_identity": EXPECTED_GENERATION,
        "qualification_identity": EXPECTED_QUALIFICATION,
        "runner_sha256": digest(runner.encode()),
        "shell_sha256": digest(shell.encode()),
        "historical_generation_rejected": True,
        "historical_qualification_rejected": True,
    }


def build(recovery_root: Path, private_root: Path, backup_root: Path, terminal_root: Path) -> dict[str, object]:
    sources = source_closure()
    predecessor = terminal_evidence(terminal_root)
    binding = runner_binding()
    report = audit_v13.audit(
        ROOT / "docs/artifacts/production-core-v13-successor-execution-authority",
        recovery_root, private_root, backup_root, recompute=True,
    )
    if report["authority_identity"] != V13_AUTHORITY or report["ed25519_verification"] != "PASS":
        raise ValueError("predecessor authority mismatch")
    v13 = json.loads((ROOT / "docs/artifacts/production-core-v13-successor-execution-authority/authority.json").read_bytes())
    if (v13["qualification_generation_identity"] != EXPECTED_GENERATION
            or v13["qualification_identity"] != EXPECTED_QUALIFICATION):
        raise ValueError("successor qualification binding mismatch")
    core = {
        "schema": "pastila-production-core-v14-successor-attempt-authority",
        "schema_version": 1,
        "status": "FROZEN_SUCCESSOR_BOUNDARY_NO_NEW_ATTEMPT",
        "bound_published_commit": SOURCE_COMMIT,
        "bound_published_tree": SOURCE_TREE,
        "predecessor_authority_identity": V13_AUTHORITY,
        "predecessor_terminal_evidence": predecessor,
        "predecessor_attempt_consumption": 1,
        "runner_binding": binding,
        "alias_secret_commitment": v13["alias_secret_commitment"],
        "schedule_sha256": v13["schedule_sha256"],
        "recovery_resolution_identity": v13["recovery_resolution_identity"],
        "runtime_object_authority_identity": v13["v12_runtime_authority_identity"],
        "source_sha256": sources,
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution_authorized": False,
        "new_attempt_consumption_authorized": False,
        "new_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }
    return {**core, "authority_identity": digest(canonical(core))}


def binding_for(authority: dict[str, object], raw: bytes) -> dict[str, object]:
    return {
        "schema": "pastila-production-core-v14-detached-attempt-binding",
        "schema_version": 1,
        "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"],
        "authority_sha256": digest(raw),
        "bound_published_commit": SOURCE_COMMIT,
        "bound_published_tree": SOURCE_TREE,
        "predecessor_attempt_identity": PREDECESSOR_ATTEMPT,
        "predecessor_terminal_failure_identity": PREDECESSOR_FAILURE,
        "predecessor_authority_identity": V13_AUTHORITY,
        "runner_binding": authority["runner_binding"],
        "recovery_resolution_identity": authority["recovery_resolution_identity"],
        "alias_secret_commitment": authority["alias_secret_commitment"],
        "schedule_sha256": authority["schedule_sha256"],
        "builder_sha256": authority["builder_sha256"],
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "new_attempt_consumption": 0,
        "candidate_execution_authorized": False,
        "new_attempt_consumption_authorized": False,
        "adjudication": False,
        "promotion": False,
    }


def materialize(recovery_root: Path, private_root: Path, backup_root: Path, terminal_root: Path, private_key: Path) -> dict[str, str]:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("V14 authority output already exists")
    signing.verify_key(private_key)
    authority = build(recovery_root, private_root, backup_root, terminal_root)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding_raw = canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v14-authority-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "authority.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(binding_raw)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin", "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")], check=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY), "-rawin", "-in", str(staging / "binding.json"), "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        result = {
            "authority_identity": authority["authority_identity"],
            "binding_identity": digest(binding_raw),
            "signature_identity": digest((staging / "binding.sig").read_bytes()),
        }
        os.replace(staging, OUTPUT)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--terminal-root", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.recovery_root, args.private_root, args.backup_root, args.terminal_root, args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
