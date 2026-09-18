"""Independently audit the signed, non-consuming R3 authority."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r3_execution_authority as issuer


def audit(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
          output: Path) -> dict:
    artifact_root = issuer.OUTPUT
    if (artifact_root.is_symlink() or not artifact_root.is_dir()
            or {path.name for path in artifact_root.iterdir()} != set(issuer.ARTIFACT_NAMES)):
        raise ValueError("R3 signed artifact set mismatch")
    paths = {name: artifact_root / name for name in issuer.ARTIFACT_NAMES}
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise ValueError("R3 signed artifact substitution")
    raw = paths["authority.json"].read_bytes()
    binding_raw = paths["binding.json"].read_bytes()
    signature = paths["binding.sig"].read_bytes()
    authority = json.loads(raw)
    core = dict(authority)
    claimed = core.pop("authority_identity", None)
    if (authority.get("schema") != "pastila-production-core-v15-r3-execution-authority"
            or claimed != issuer.digest(issuer.canonical(core))
            or authority.get("publication_parent_commit") != issuer.R2_COMMIT
            or authority.get("historical_r2", {}).get("attempt_identity") != issuer.R2_ATTEMPT
            or authority.get("output", {}).get("path") != str(issuer.R3_OUTPUT)
            or authority.get("output", {}).get("entries") != 0
            or authority.get("candidate_execution") != 0
            or authority.get("attempt_consumption") != 0
            or authority.get("candidate_execution_authorized") is not False
            or authority.get("attempt_consumption_authorized") is not False
            or authority.get("adjudication") is not False
            or authority.get("promotion") is not False):
        raise ValueError("R3 authority identity or state rejected")
    if (raw != json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            or paths["builder-source.py"].read_bytes() !=
            (issuer.ROOT / "scripts/materialize_production_core_v15_r3_execution_authority.py").read_bytes()
            or binding_raw != issuer.canonical(issuer.binding_for(authority, raw))
            or len(signature) != 64):
        raise ValueError("R3 binding, builder, or signature representation drift")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
                    str(signing.PUBLIC_KEY), "-rawin", "-in", str(paths["binding.json"]),
                    "-sigfile", str(paths["binding.sig"])], check=True, capture_output=True)
    for name, expected in authority["source_sha256"].items():
        path = issuer.ROOT / name
        if path.is_symlink() or issuer.digest(path.read_bytes()) != expected:
            raise ValueError(f"R3 source drift: {name}")
    signed_ids = (claimed, issuer.digest(binding_raw), issuer.digest(signature))
    if any(any(value.encode() in (issuer.ROOT / name).read_bytes() for value in signed_ids)
           for name in issuer.NEW_SOURCES):
        raise ValueError("R3 signed source dependency cycle")
    if authority != issuer.build(recovery, private, backup, v13_terminal,
                                 terminal, rootfs, snapshot, unicode_root, output):
        raise ValueError("R3 source/runtime/evidence reproduction mismatch")
    return {
        "verdict": "PASS + 0 BLOCKERS", "authority_identity": claimed,
        "binding_identity": issuer.digest(binding_raw),
        "signature_identity": issuer.digest(signature),
        "ed25519_verification": "PASS", "source_closure": "PASS",
        "runtime_object_closure": "PASS", "snapshot_closure": "PASS",
        "isolated_cuda": "PASS", "r2_historical_evidence": "UNCHANGED",
        "v14_terminal_evidence": "UNCHANGED", "output": "EMPTY_NATIVE_EXT4",
        "candidate_execution": 0, "attempt_consumption": 0,
        "adjudication": False, "promotion": False, "authority": authority,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs",
                 "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.recovery, args.private, args.backup, args.v13_terminal,
                   args.terminal, args.rootfs, args.snapshot, args.unicode_root,
                   args.output)
    report.pop("authority")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
