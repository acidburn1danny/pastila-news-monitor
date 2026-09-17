"""Independent read-only audit of the signed V12 recovery-bound authority."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import materialize_production_core_successor_execution_authority_v12 as authority_v12

EXPECTED = {"authority.json", "binding.json", "binding.sig", "builder-source.py"}


def audit(output: Path, recovery_root: Path, *, recompute: bool = True) -> dict[str, str]:
    if output.is_symlink() or not output.is_dir() or {p.name for p in output.iterdir()} != EXPECTED:
        raise ValueError("authority artifact closure mismatch")
    files = {name: output / name for name in EXPECTED}
    if any(path.is_symlink() or not path.is_file() for path in files.values()):
        raise ValueError("authority artifact symlink or non-file")
    raw = files["authority.json"].read_bytes()
    binding_raw = files["binding.json"].read_bytes()
    signature = files["binding.sig"].read_bytes()
    authority = json.loads(raw)
    core = dict(authority)
    claimed = core.pop("authority_identity", None)
    if claimed != authority_v12.digest(authority_v12.canonical(core)):
        raise ValueError("authority seal mismatch")
    if authority.get("schema") != "pastila-production-core-successor-execution-authority-v12" or authority.get("schema_version") != 1 or authority.get("status") != "FROZEN_V12_RECOVERY_BOUND_ZERO_ATTEMPTS":
        raise ValueError("V12 authority schema or status mismatch")
    if authority.get("bound_source_commit") != authority_v12.COMMIT or authority.get("bound_source_tree") != authority_v12.TREE or authority.get("runner_v12_identity") != authority_v12.RUNNER or authority.get("recovery_resolution_identity") != authority_v12.RESOLUTION:
        raise ValueError("canonical source or recovery binding mismatch")
    if type(authority.get("candidate_execution")) is not int or authority["candidate_execution"] != 0 or type(authority.get("successor_attempt_consumption")) is not int or authority["successor_attempt_consumption"] != 0 or authority.get("adjudication") is not False or authority.get("promotion") is not False or authority.get("candidate_execution_authorized") is not False or authority.get("attempt_consumption_authorized") is not False:
        raise ValueError("authority execution state mismatch")
    if authority_v12.digest(files["builder-source.py"].read_bytes()) != authority.get("builder_sha256"):
        raise ValueError("builder source closure mismatch")
    expected_binding = authority_v12.canonical(authority_v12.binding_for(authority, raw))
    if binding_raw != expected_binding or len(signature) != 64:
        raise ValueError("binding bytes or signature shape mismatch")
    subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(authority_v12.PUBLIC_KEY), "-rawin", "-in", str(files["binding.json"]), "-sigfile", str(files["binding.sig"])],
        check=True, capture_output=True,
    )
    if recompute:
        rebuilt = authority_v12.build(recovery_root)
        if authority != rebuilt:
            raise ValueError("authority does not reproduce published recovery boundary")
    return {
        "authority_identity": authority["authority_identity"],
        "binding_identity": authority_v12.digest(binding_raw),
        "signature_identity": authority_v12.digest(signature),
        "ed25519_verification": "PASS",
        "source_closure": "PASS" if recompute else "NOT_RECOMPUTED",
        "runtime_object_closure": "PASS" if recompute else "NOT_RECOMPUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--recovery-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.authority_root, args.recovery_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
