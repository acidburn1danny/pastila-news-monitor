"""Read-only audit of the private V13 alias secret and public successor schedule."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import materialize_production_core_successor_qualification_generation_v13 as generation_v13


def audit(private_root: Path, backup_root: Path) -> dict[str, str]:
    primary = private_root / generation_v13.SECRET_NAME
    backup = backup_root / generation_v13.SECRET_NAME
    if (str(private_root).startswith("/mnt/") or private_root.is_symlink()
            or backup_root.is_symlink() or backup.is_symlink()):
        raise ValueError("secret root substitution")
    secret = generation_v13.read_secret(primary)
    raw_secret = generation_v13.secret_bytes(secret)
    if not backup.is_file() or backup.read_bytes() != raw_secret:
        raise ValueError("owner-held secret backup mismatch")
    expected_generation, expected_qualification = generation_v13.build(secret)
    for path, expected, identity in (
        (generation_v13.GENERATION, expected_generation, "qualification_generation_identity"),
        (generation_v13.QUALIFICATION, expected_qualification, "qualification_identity"),
    ):
        observed = generation_v13.read_json(path)
        generation_v13.check_seal(observed, identity)
        if observed != expected or path.read_bytes() != json.dumps(expected, ensure_ascii=False, indent=2).encode() + b"\n":
            raise ValueError(f"successor artifact does not reproduce: {path.name}")
    if expected_generation["alias_secret_commitment"] != generation_v13.digest(raw_secret):
        raise ValueError("secret commitment mismatch")
    if expected_generation["alias_secret_commitment"] == generation_v13.HISTORICAL:
        raise ValueError("historical secret reused")
    rows = expected_generation["schedule"]
    if len(rows) != 2400 or len({(r["materialization"], r["repetition"], r["candidate_alias"], r["case_id"]) for r in rows}) != 2400:
        raise ValueError("successor matrix incomplete")
    return {
        "alias_secret_commitment": expected_generation["alias_secret_commitment"],
        "qualification_generation_identity": expected_generation["qualification_generation_identity"],
        "qualification_identity": expected_qualification["qualification_identity"],
        "secret_backup": "BYTE_EXACT",
        "source_closure": "PASS",
        "matrix": "2400_UNIQUE_ROWS",
        "candidate_execution": "0",
        "successor_attempt_consumption": "0",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.private_root, args.backup_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
