"""Verify the signed execution-bound preflight authority without an attempt."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_v15_execution_bound_preflight_r2 as issuer
import materialize_production_core_successor_execution_authority_v12 as signing

EXPECTED = {"authority.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, output: Path) -> dict:
    root = issuer.OUTPUT
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != EXPECTED:
        raise ValueError("bound preflight artifact set mismatch")
    files = {name: root / name for name in EXPECTED}
    if any(path.is_symlink() or not path.is_file() for path in files.values()):
        raise ValueError("bound preflight artifact substitution")
    raw = files["authority.json"].read_bytes()
    binding_raw = files["binding.json"].read_bytes()
    signature = files["binding.sig"].read_bytes()
    authority = json.loads(raw)
    core = dict(authority)
    claimed = core.pop("authority_identity", None)
    if (authority.get("schema") != "pastila-production-core-v15-execution-bound-preflight-r2-authority"
            or claimed != issuer.digest(issuer.canonical(core))
            or authority.get("published_base_commit") != issuer.BASE_COMMIT
            or authority.get("base_authority_identity") != issuer.BASE_AUTHORITY
            or authority.get("candidate_execution") != 0
            or authority.get("attempt_consumption") != 0
            or authority.get("adjudication") is not False
            or authority.get("promotion") is not False):
        raise ValueError("bound preflight authority identity rejected")
    if (raw != json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            or files["builder-source.py"].read_bytes() != (issuer.ROOT / "scripts/materialize_production_core_v15_execution_bound_preflight_r2.py").read_bytes()
            or binding_raw != issuer.canonical(issuer.binding_for(authority, raw))
            or len(signature) != 64):
        raise ValueError("bound preflight binding or builder mismatch")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
                    "-rawin", "-in", str(files["binding.json"]), "-sigfile", str(files["binding.sig"])],
                   check=True, capture_output=True)
    new_identities = tuple(value.encode() for value in
                           (claimed, issuer.digest(binding_raw), issuer.digest(signature)))
    if any(any(identity in (issuer.ROOT / name).read_bytes() for identity in new_identities)
           for name in issuer.NEW_SOURCES):
        raise ValueError("execution-bound dependency cycle detected")
    if authority != issuer.build(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output):
        raise ValueError("bound preflight source/runtime reproduction mismatch")
    return {"verdict": "PASS + 0 BLOCKERS", "authority_identity": claimed,
            "binding_identity": issuer.digest(binding_raw), "signature_identity": issuer.digest(signature),
            "ed25519_verification": "PASS", "source_closure": "PASS", "runtime_object_closure": "PASS",
            "snapshot_closure": "PASS", "output": "EMPTY_NATIVE_EXT4", "authority": authority}


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    report = audit(a.recovery, a.private, a.backup, a.v13_terminal, a.terminal, a.rootfs, a.snapshot, a.output)
    del report["authority"]
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
