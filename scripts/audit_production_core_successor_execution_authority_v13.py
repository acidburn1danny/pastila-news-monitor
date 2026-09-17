"""Fresh read-only audit of the signed V13 successor authority."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_successor_execution_authority_v13 as authority_v13
import materialize_production_core_successor_execution_authority_v12 as authority_v12

EXPECTED = {"authority.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(output: Path, recovery_root: Path, private_root: Path, backup_root: Path, *, recompute: bool = True) -> dict[str, str]:
    if output.is_symlink() or not output.is_dir() or {p.name for p in output.iterdir()} != EXPECTED:
        raise ValueError("V13 authority artifact closure mismatch")
    paths = {name: output / name for name in EXPECTED}
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise ValueError("V13 authority artifact substitution")
    raw = paths["authority.json"].read_bytes()
    binding_raw = paths["binding.json"].read_bytes()
    signature = paths["binding.sig"].read_bytes()
    authority = json.loads(raw)
    core = dict(authority)
    identity = core.pop("authority_identity", None)
    if identity != authority_v12.digest(authority_v12.canonical(core)):
        raise ValueError("V13 authority seal mismatch")
    if (authority.get("schema") != "pastila-production-core-successor-execution-authority-v13"
            or authority.get("schema_version") != 1
            or authority.get("status") != "FROZEN_V13_NEW_ALIAS_SECRET_ZERO_ATTEMPTS"
            or authority.get("bound_source_commit") != authority_v13.COMMIT
            or authority.get("bound_source_tree") != authority_v13.TREE
            or authority.get("runner_v12_identity") != authority_v13.RUNNER
            or authority.get("recovery_resolution_identity") != authority_v13.RESOLUTION):
        raise ValueError("V13 source or recovery binding mismatch")
    if (authority.get("alias_secret_commitment") == authority_v13.generation_v13.HISTORICAL
            or type(authority.get("candidate_execution")) is not int or authority["candidate_execution"] != 0
            or type(authority.get("successor_attempt_consumption")) is not int or authority["successor_attempt_consumption"] != 0
            or authority.get("adjudication") is not False or authority.get("promotion") is not False
            or authority.get("candidate_execution_authorized") is not False
            or authority.get("attempt_consumption_authorized") is not False):
        raise ValueError("V13 authority execution boundary mismatch")
    if authority_v12.digest(paths["builder-source.py"].read_bytes()) != authority.get("builder_sha256"):
        raise ValueError("V13 builder source mismatch")
    if raw != json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n":
        raise ValueError("V13 authority byte representation mismatch")
    expected_binding = authority_v12.canonical(authority_v13.binding_for(authority, raw))
    if binding_raw != expected_binding or len(signature) != 64:
        raise ValueError("V13 detached binding mismatch")
    subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(authority_v13.PUBLIC_KEY), "-rawin", "-in", str(paths["binding.json"]), "-sigfile", str(paths["binding.sig"])],
        check=True, capture_output=True,
    )
    if recompute and authority != authority_v13.build(recovery_root, private_root, backup_root):
        raise ValueError("V13 authority does not reproduce source/runtime boundary")
    return {
        "authority_identity": identity,
        "binding_identity": authority_v12.digest(binding_raw),
        "signature_identity": authority_v12.digest(signature),
        "ed25519_verification": "PASS",
        "source_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "runtime_object_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "qualification_schedule_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "candidate_execution": "0",
        "successor_attempt_consumption": "0",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, default=authority_v13.OUTPUT)
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.authority_root, args.recovery_root, args.private_root, args.backup_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
