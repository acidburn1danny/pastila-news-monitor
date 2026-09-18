"""Fresh read-only audit of the signed V14 successor attempt boundary."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_successor_attempt_authority_v14 as boundary
import materialize_production_core_successor_execution_authority_v12 as signing

EXPECTED = {"authority.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(recovery_root: Path, private_root: Path, backup_root: Path, terminal_root: Path, *, recompute: bool = True) -> dict[str, str]:
    output = boundary.OUTPUT
    if output.is_symlink() or not output.is_dir() or {p.name for p in output.iterdir()} != EXPECTED:
        raise ValueError("V14 authority artifact closure mismatch")
    paths = {name: output / name for name in EXPECTED}
    if any(p.is_symlink() or not p.is_file() for p in paths.values()):
        raise ValueError("V14 artifact substitution")
    raw = paths["authority.json"].read_bytes()
    binding_raw = paths["binding.json"].read_bytes()
    signature = paths["binding.sig"].read_bytes()
    authority = json.loads(raw)
    core = dict(authority)
    identity = core.pop("authority_identity", None)
    if identity != boundary.digest(boundary.canonical(core)):
        raise ValueError("V14 authority seal mismatch")
    if (authority.get("schema") != "pastila-production-core-v14-successor-attempt-authority"
            or authority.get("schema_version") != 1
            or authority.get("status") != "FROZEN_SUCCESSOR_BOUNDARY_NO_NEW_ATTEMPT"
            or authority.get("bound_published_commit") != boundary.SOURCE_COMMIT
            or authority.get("bound_published_tree") != boundary.SOURCE_TREE
            or authority.get("predecessor_authority_identity") != boundary.V13_AUTHORITY
            or authority.get("predecessor_attempt_consumption") != 1
            or authority.get("new_attempt_consumption") != 0
            or authority.get("candidate_execution_authorized") is not False
            or authority.get("new_attempt_consumption_authorized") is not False
            or authority.get("adjudication") is not False
            or authority.get("promotion") is not False):
        raise ValueError("V14 execution boundary mismatch")
    if boundary.digest(paths["builder-source.py"].read_bytes()) != authority.get("builder_sha256"):
        raise ValueError("V14 builder source mismatch")
    if raw != json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n":
        raise ValueError("V14 authority representation mismatch")
    if binding_raw != boundary.canonical(boundary.binding_for(authority, raw)) or len(signature) != 64:
        raise ValueError("V14 detached binding mismatch")
    subprocess.run([
        "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
        "-rawin", "-in", str(paths["binding.json"]), "-sigfile", str(paths["binding.sig"]),
    ], check=True, capture_output=True)
    if recompute and authority != boundary.build(recovery_root, private_root, backup_root, terminal_root):
        raise ValueError("V14 source/runtime/terminal evidence reproduction mismatch")
    return {
        "verdict": "PASS + 0 BLOCKERS",
        "authority_identity": identity,
        "binding_identity": boundary.digest(binding_raw),
        "signature_identity": boundary.digest(signature),
        "ed25519_verification": "PASS",
        "runner_binding": "PASS" if recompute else "NOT_RECOMPUTED",
        "source_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "runtime_object_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "qualification_schedule_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "predecessor_terminal_evidence": "PASS" if recompute else "NOT_RECOMPUTED",
        "new_attempt_consumption": "0",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--terminal-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.recovery_root, args.private_root, args.backup_root, args.terminal_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
