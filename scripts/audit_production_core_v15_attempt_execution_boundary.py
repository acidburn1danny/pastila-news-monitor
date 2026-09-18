"""Fresh adversarial audit of the signed V15 attempt route, without execution."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_v15_attempt_execution_boundary as issuer
import materialize_production_core_successor_execution_authority_v12 as signing

EXPECTED = {"boundary.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, output: Path) -> dict:
    root = issuer.OUTPUT
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != EXPECTED:
        raise ValueError("V15 attempt artifact set mismatch")
    paths = {name: root / name for name in EXPECTED}
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise ValueError("V15 attempt artifact substitution")
    raw = paths["boundary.json"].read_bytes()
    binding_raw = paths["binding.json"].read_bytes()
    signature = paths["binding.sig"].read_bytes()
    boundary = json.loads(raw)
    core = dict(boundary)
    recorded = core.pop("boundary_identity", None)
    if (recorded != issuer.digest(issuer.canonical(core))
            or boundary.get("schema") != "pastila-production-core-v15-attempt-execution-boundary"
            or boundary.get("status") != "SIGNED_NO_CANDIDATE_NO_ATTEMPT"
            or boundary.get("published_v15_preflight_commit") != issuer.PREFLIGHT_COMMIT
            or boundary.get("v15_authority_identity") != issuer.V15_AUTHORITY
            or boundary.get("v15_binding_identity") != issuer.V15_BINDING
            or boundary.get("v15_signature_identity") != issuer.V15_SIGNATURE
            or boundary.get("shell_argument_count") != 16
            or boundary.get("candidate_execution") != 0
            or boundary.get("attempt_consumption") != 0
            or boundary.get("candidate_execution_authorized") is not False
            or boundary.get("attempt_consumption_authorized") is not False
            or boundary.get("adjudication") is not False
            or boundary.get("promotion") is not False):
        raise ValueError("V15 attempt identity or state mismatch")
    if (raw != json.dumps(boundary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            or issuer.digest(paths["builder-source.py"].read_bytes()) != boundary["builder_sha256"]
            or binding_raw != issuer.canonical(issuer.binding_for(boundary, raw))
            or len(signature) != 64):
        raise ValueError("V15 attempt detached binding mismatch")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
                    "-rawin", "-in", str(paths["binding.json"]),
                    "-sigfile", str(paths["binding.sig"])], check=True, capture_output=True)
    if boundary != issuer.build(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output):
        raise ValueError("V15 attempt source/runtime/output reproduction mismatch")
    return {"verdict": "PASS + 0 BLOCKERS", "boundary_identity": recorded,
            "binding_identity": issuer.digest(binding_raw),
            "signature_identity": issuer.digest(signature),
            "ed25519_verification": "PASS", "source_closure": "PASS",
            "runtime_object_closure": "PASS", "snapshot_closure": "PASS",
            "v14_terminal_closure": "PASS", "output": "EMPTY_NATIVE_EXT4",
            "candidate_execution": "0", "attempt_consumption": "0",
            "adjudication": "false", "promotion": "false", "boundary": boundary}


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.recovery, args.private, args.backup, args.v13_terminal,
                   args.terminal, args.rootfs, args.snapshot, args.output)
    del result["boundary"]
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
