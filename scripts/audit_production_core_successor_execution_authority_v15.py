"""Fresh adversarial audit of the signed V15 driver-bound authority."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_successor_execution_authority_v15 as boundary
import materialize_production_core_successor_execution_authority_v12 as signing

EXPECTED = {"authority.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path) -> dict[str, str]:
    output = boundary.OUTPUT
    if output.is_symlink() or not output.is_dir() or {p.name for p in output.iterdir()} != EXPECTED:
        raise ValueError("V15 authority artifact set mismatch")
    paths = {name: output / name for name in EXPECTED}
    if any(p.is_symlink() or not p.is_file() for p in paths.values()):
        raise ValueError("V15 authority artifact substitution")
    raw = paths["authority.json"].read_bytes()
    binding_raw = paths["binding.json"].read_bytes()
    signature = paths["binding.sig"].read_bytes()
    authority = json.loads(raw)
    core = dict(authority)
    identity = core.pop("authority_identity", None)
    if (identity != boundary.digest(boundary.canonical(core))
            or authority.get("schema") != "pastila-production-core-v15-successor-execution-authority"
            or authority.get("schema_version") != 1
            or authority.get("status") != "SIGNED_DRIVER_BOUND_SUCCESSOR_NO_ATTEMPT"
            or authority.get("bound_published_v14_commit") != boundary.design.SOURCE_COMMIT
            or authority.get("bound_published_v14_tree") != boundary.design.SOURCE_TREE
            or authority.get("predecessor_v14_authority_identity") != boundary.V14_AUTHORITY
            or authority.get("predecessor_v14_attempt_consumption") != 1
            or authority.get("new_candidate_execution") != 0
            or authority.get("new_attempt_consumption") != 0
            or authority.get("candidate_execution_authorized") is not False
            or authority.get("new_attempt_consumption_authorized") is not False
            or authority.get("adjudication") is not False
            or authority.get("promotion") is not False):
        raise ValueError("V15 authority identity or execution state mismatch")
    if (raw != json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            or boundary.digest(paths["builder-source.py"].read_bytes()) != authority.get("builder_sha256")
            or binding_raw != boundary.canonical(boundary.binding_for(authority, raw))
            or len(signature) != 64):
        raise ValueError("V15 authority representation or detached binding mismatch")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
                    "-rawin", "-in", str(paths["binding.json"]), "-sigfile", str(paths["binding.sig"])],
                   check=True, capture_output=True)
    if authority != boundary.build(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot):
        raise ValueError("V15 source/runtime/GPU/terminal reproduction mismatch")
    return {
        "verdict": "PASS + 0 BLOCKERS",
        "authority_identity": identity,
        "binding_identity": boundary.digest(binding_raw),
        "signature_identity": boundary.digest(signature),
        "ed25519_verification": "PASS",
        "source_closure": "PASS",
        "v14_terminal_closure": "PASS",
        "runtime_object_closure": "PASS",
        "driver_snapshot_closure": "PASS",
        "isolated_cuda": "PASS",
        "new_candidate_execution": "0",
        "new_attempt_consumption": "0",
        "adjudication": "false",
        "promotion": "false",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.recovery, args.private, args.backup, args.v13_terminal,
                           args.terminal, args.rootfs, args.snapshot), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
