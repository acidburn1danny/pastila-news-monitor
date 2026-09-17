"""Read-only Ed25519 and source audit of the V13 launcher boundary."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_v13_launcher_boundary as launcher_boundary
import materialize_production_core_successor_execution_authority_v12 as signing

EXPECTED = {"boundary.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(output: Path = launcher_boundary.OUTPUT) -> dict[str, str]:
    if output.is_symlink() or not output.is_dir() or {p.name for p in output.iterdir()} != EXPECTED:
        raise ValueError("launcher boundary artifact closure mismatch")
    files = {name: output / name for name in EXPECTED}
    if any(path.is_symlink() or not path.is_file() for path in files.values()):
        raise ValueError("launcher boundary artifact substitution")
    raw = files["boundary.json"].read_bytes()
    binding_raw = files["binding.json"].read_bytes()
    signature = files["binding.sig"].read_bytes()
    boundary = json.loads(raw)
    core = dict(boundary)
    recorded = core.pop("boundary_identity", None)
    if (recorded != launcher_boundary.digest(launcher_boundary.canonical(core))
            or boundary.get("schema") != "pastila-production-core-v13-preconsumption-launcher-boundary"
            or boundary.get("schema_version") != 1
            or boundary.get("status") != "SIGNED_PREFLIGHT_ONLY_ZERO_ATTEMPTS"
            or boundary.get("v13_authority_identity") != launcher_boundary.AUTHORITY_ID
            or type(boundary.get("candidate_execution")) is not int or boundary["candidate_execution"] != 0
            or type(boundary.get("successor_attempt_consumption")) is not int or boundary["successor_attempt_consumption"] != 0
            or boundary.get("candidate_execution_authorized") is not False
            or boundary.get("attempt_consumption_authorized") is not False
            or boundary.get("adjudication") is not False or boundary.get("promotion") is not False):
        raise ValueError("launcher boundary identity or execution state mismatch")
    if (raw != json.dumps(boundary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            or launcher_boundary.digest(files["builder-source.py"].read_bytes()) != boundary.get("builder_sha256")):
        raise ValueError("launcher builder or byte representation mismatch")
    if binding_raw != launcher_boundary.canonical(launcher_boundary.binding_for(boundary, raw)) or len(signature) != 64:
        raise ValueError("launcher detached binding mismatch")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
                    "-rawin", "-in", str(files["binding.json"]), "-sigfile", str(files["binding.sig"])],
                   check=True, capture_output=True)
    if boundary != launcher_boundary.build():
        raise ValueError("launcher source closure mismatch")
    return {"boundary_identity": recorded, "binding_identity": launcher_boundary.digest(binding_raw),
            "signature_identity": launcher_boundary.digest(signature), "ed25519_verification": "PASS",
            "source_closure": "PASS", "candidate_execution": "0", "successor_attempt_consumption": "0"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary-root", type=Path, default=launcher_boundary.OUTPUT)
    args = parser.parse_args()
    print(json.dumps(audit(args.boundary_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
