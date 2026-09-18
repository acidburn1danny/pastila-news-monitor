"""Publication-bound R3 pre-consumption receipt; never creates an attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import audit_production_core_v15_r3_execution_authority as signed
import materialize_production_core_v15_r3_execution_authority as issuer
import preflight_production_core_candidate_qualification_v15 as legacy
from pastila_scout import production_core_successor_contract_v15_r3 as contract

SCHEMA = "pastila-production-core-v15-r3-preconsumption-receipt"
LIFETIME_NS = 900_000_000_000


def current_publication(authority: dict) -> tuple[str, str]:
    """Reject an unpublished route or a commit other than the exact R3 successor."""
    ref = f"refs/heads/{issuer.BRANCH}"
    parts = issuer.git("ls-remote", "--heads", "origin", ref).split()
    head = issuer.git("rev-parse", "HEAD")
    if len(parts) != 2 or parts[1] != ref or parts[0] != head:
        raise ValueError("R3 unpublished or remote ref drift")
    if issuer.git("show", "-s", "--format=%P", head) != issuer.R2_COMMIT:
        raise ValueError("R3 publication parent must be consumed R2 checkpoint")
    required = set(issuer.NEW_SOURCES) | {
        f"docs/artifacts/production-core-v15-r3-execution-authority/{name}"
        for name in issuer.ARTIFACT_NAMES
    }
    committed = set(issuer.git("diff-tree", "--no-commit-id", "--name-only", "-r", head).splitlines())
    if committed != required:
        raise ValueError("R3 published file scope mismatch")
    for name, expected in authority["source_sha256"].items():
        if hashlib.sha256(subprocess.check_output(["git", "show", f"{head}:{name}"],
                                           cwd=issuer.ROOT)).hexdigest() != expected:
            raise ValueError(f"R3 unpublished source: {name}")
    for name in issuer.ARTIFACT_NAMES:
        relative = f"docs/artifacts/production-core-v15-r3-execution-authority/{name}"
        if (issuer.ROOT / relative).read_bytes() != subprocess.check_output(
                ["git", "show", f"{head}:{relative}"], cwd=issuer.ROOT):
            raise ValueError(f"R3 unpublished signed artifact: {name}")
    return head, issuer.git("show", "-s", "--format=%T", head)


def issue(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
          output: Path) -> dict:
    if output != issuer.R3_OUTPUT or output != output.resolve(strict=True):
        raise ValueError("R3 canonical output path mismatch")
    report = signed.audit(recovery, private, backup, v13_terminal,
                          terminal, rootfs, snapshot, unicode_root, output)
    authority = report["authority"]
    commit, tree = current_publication(authority)
    old = legacy.preflight(recovery, private, backup, v13_terminal, terminal,
                           rootfs, snapshot, unicode_root, output)
    if old["preflight_identity"] != authority["legacy_preflight_identity"]:
        raise ValueError("R3 legacy runtime preflight drift")
    manifest = json.loads((issuer.ROOT / "docs/artifacts/production-core-candidate-request-manifest-v2.json").read_bytes())
    if len(contract.validate_manifest_contract(manifest)) != 200:
        raise ValueError("R3 validator request contract drift")
    state = legacy.empty_output(output, (issuer.ROOT, recovery, private, backup, v13_terminal,
                                         terminal, rootfs, snapshot, unicode_root, issuer.R2_OUTPUT))
    if state != authority["output"] or (output / "attempt.json").exists():
        raise ValueError("R3 output or attempt drift")
    secret = private / "candidate-alias-secret-v13.json"
    if secret.is_symlink() or issuer.digest(secret.read_bytes()) != authority["alias_secret_commitment"]:
        raise ValueError("R3 V13 secret commitment drift")
    now = time.time_ns()
    core = {
        "schema": SCHEMA, "schema_version": 1, "verdict": "PASS + 0 BLOCKERS",
        "published_commit": commit, "published_tree": tree,
        "publication_parent_commit": issuer.R2_COMMIT,
        "authority_identity": report["authority_identity"],
        "binding_identity": report["binding_identity"],
        "signature_identity": report["signature_identity"],
        "historical_r2_attempt_identity": issuer.R2_ATTEMPT,
        "v14_terminal_failure_sha256": issuer.V14_TERMINAL_SHA256,
        "legacy_preflight_identity": old["preflight_identity"],
        "qualification_generation_identity": authority["qualification_generation_identity"],
        "qualification_identity": authority["qualification_identity"],
        "r3_projected_mechanics_sha256": authority["r3_projected_mechanics_sha256"],
        "bound_executor_sha256": authority["bound_executor_sha256"],
        "bound_preflight_sha256": authority["bound_preflight_sha256"],
        "driver_snapshot": authority["driver_snapshot"],
        "output": state, "attempt_json": "ABSENT",
        "issued_at_ns": now, "expires_at_ns": now + LIFETIME_NS,
        "issuer_pid": os.getpid(), "candidate_execution": 0,
        "attempt_consumption": 0, "adjudication": False, "promotion": False,
    }
    return {**core, "receipt_identity": issuer.digest(issuer.canonical(core))}


def verify_receipt(receipt: dict, authority: dict, expected: dict,
                   private: Path, output: Path, protected: tuple[Path, ...]) -> None:
    if not isinstance(receipt, dict) or receipt != expected:
        raise ValueError("R3 receipt substitution")
    core = dict(receipt)
    claimed = core.pop("receipt_identity", None)
    if (claimed != issuer.digest(issuer.canonical(core))
            or receipt.get("schema") != SCHEMA
            or receipt.get("authority_identity") != authority["authority_identity"]
            or receipt.get("legacy_preflight_identity") != authority["legacy_preflight_identity"]
            or receipt.get("issuer_pid") != os.getpid()):
        raise ValueError("R3 receipt identity rejected")
    now = time.time_ns()
    if not receipt["issued_at_ns"] <= now <= receipt["expires_at_ns"]:
        raise ValueError("R3 receipt expired")
    if current_publication(authority) != (receipt["published_commit"], receipt["published_tree"]):
        raise ValueError("R3 publication changed")
    if (legacy.empty_output(output, protected) != receipt["output"]
            or (output / "attempt.json").exists()):
        raise ValueError("R3 output changed")
    secret = private / "candidate-alias-secret-v13.json"
    if secret.is_symlink() or issuer.digest(secret.read_bytes()) != authority["alias_secret_commitment"]:
        raise ValueError("R3 secret changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs",
                 "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(issue(args.recovery, args.private, args.backup, args.v13_terminal,
                           args.terminal, args.rootfs, args.snapshot,
                           args.unicode_root, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
