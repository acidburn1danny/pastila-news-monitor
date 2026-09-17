"""Open a separate candidate-neutral generation after loss of the V2 alias secret."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
HISTORICAL = "ee86684da529d0b1a75c172d5ed2c3ec65f21da5f350d53cb7dda500f4449dca"
SOURCE_GENERATION = ART / "production-core-successor-comparative-qualification-generation-v10.json"
SOURCE_QUALIFICATION = ART / "production-core-successor-candidate-generation-qualification-v10.json"
REQUESTS = ART / "production-core-candidate-request-manifest-v2.json"
CANDIDATES = ART / "production-core-successor-candidate-object-manifest-v10.json"
GENERATION = ART / "production-core-successor-comparative-qualification-generation-v13.json"
QUALIFICATION = ART / "production-core-successor-candidate-generation-qualification-v13.json"
ALIASES = ("CANDIDATE-A", "CANDIDATE-B")
CANDIDATE_NAMES = (
    "pastila-editor-core-v1.1-json-successor-v2",
    "pastila-editor-core-v1.2-json-successor",
)
SECRET_NAME = "candidate-alias-secret-v13.json"
SOURCE_COMMIT = "ea428931f95a65131ed7def90e9c17f488bd714b"
SOURCE_TREE = "0e5038566f6b1cb9a3b725cccf00b2fe403c7aaa"
INDEPENDENT_INPUTS = (
    SOURCE_GENERATION,
    SOURCE_QUALIFICATION,
    REQUESTS,
    CANDIDATES,
    ART / "production-core-candidate-input-envelope-a-v2.json",
    ART / "production-core-candidate-input-envelope-b-v2.json",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sealed(core: dict, field: str) -> dict:
    return {**core, field: digest(canonical(core))}


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"authority input unavailable: {path.name}")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"authority input malformed: {path.name}")
    return value


def check_seal(value: dict, field: str) -> None:
    core = dict(value)
    claimed = core.pop(field, None)
    if claimed != digest(canonical(core)):
        raise ValueError(f"authority seal mismatch: {field}")


def source_closure() -> None:
    tree = subprocess.check_output(["git", "rev-parse", f"{SOURCE_COMMIT}^{{tree}}"], cwd=ROOT).strip().decode()
    if tree != SOURCE_TREE:
        raise ValueError("published source tree mismatch")
    for path in INDEPENDENT_INPUTS:
        name = path.relative_to(ROOT).as_posix()
        committed = subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{name}"], cwd=ROOT)
        if path.is_symlink() or path.read_bytes() != committed:
            raise ValueError(f"independent input changed: {name}")


def secret_bytes(value: dict) -> bytes:
    if (tuple(value) != ("schema", "schema_version", "nonce_hex", "aliases")
            or value["schema"] != "pastila-production-core-candidate-alias-secret"
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(value["nonce_hex"], str) or len(value["nonce_hex"]) != 64
            or any(c not in "0123456789abcdef" for c in value["nonce_hex"])
            or not isinstance(value["aliases"], dict)
            or tuple(value["aliases"]) != ALIASES
            or set(value["aliases"].values()) != set(CANDIDATE_NAMES)):
        raise ValueError("candidate alias secret malformed")
    return canonical(value)


def read_secret(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("candidate alias secret unavailable")
    if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_mode & 0o077:
        raise ValueError("candidate alias secret permissions rejected")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict) or path.read_bytes() != secret_bytes(value):
        raise ValueError("candidate alias secret bytes rejected")
    return value


def create_secret(private_root: Path, backup_root: Path) -> tuple[dict, str]:
    if str(private_root).startswith("/mnt/") or private_root.is_symlink() or backup_root.is_symlink():
        raise ValueError("private secret requires native ext4 and non-symlink roots")
    private_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if private_root.stat().st_mode & 0o077:
        raise ValueError("private secret root permissions rejected")
    backup_root.mkdir(parents=True, exist_ok=True)
    primary = private_root / SECRET_NAME
    backup = backup_root / SECRET_NAME
    if primary.exists() or backup.exists():
        if not primary.is_file() or not backup.is_file() or backup.is_symlink():
            raise ValueError("incomplete or substituted secret copies")
        value = read_secret(primary)
        raw = secret_bytes(value)
        if backup.read_bytes() != raw:
            raise ValueError("secret backup mismatch")
        return value, digest(raw)
    names = list(CANDIDATE_NAMES)
    if secrets.randbits(1):
        names.reverse()
    value = {
        "schema": "pastila-production-core-candidate-alias-secret",
        "schema_version": 1,
        "nonce_hex": secrets.token_hex(32),
        "aliases": dict(zip(ALIASES, names, strict=True)),
    }
    raw = secret_bytes(value)
    if digest(raw) == HISTORICAL:
        raise ValueError("new secret collided with historical commitment")
    for path, mode in ((primary, 0o600), (backup, 0o600)):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
        try:
            os.write(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)
    if read_secret(primary) != value or backup.read_bytes() != raw:
        raise ValueError("new secret copy verification failed")
    return value, digest(raw)


def schedule(case_ids: list[str], secret: dict) -> list[dict]:
    secret_bytes(secret)
    if len(case_ids) != 200 or len(set(case_ids)) != 200:
        raise ValueError("frozen request case set mismatch")
    key = bytes.fromhex(secret["nonce_hex"])
    rows: list[dict] = []
    for label in ("A", "B"):
        for repetition in (1, 2, 3):
            for alias in ALIASES:
                ordered = sorted(case_ids, key=lambda case_id: (
                    hmac.digest(key, f"{label}\0{repetition}\0{alias}\0{case_id}".encode(), "sha256"),
                    case_id,
                ))
                for ordinal, case_id in enumerate(ordered, 1):
                    rows.append({
                        "global_ordinal": len(rows) + 1,
                        "materialization": label,
                        "repetition": repetition,
                        "candidate_alias": alias,
                        "batch_ordinal": ordinal,
                        "case_id": case_id,
                    })
    if len(rows) != 2400:
        raise ValueError("successor schedule cardinality mismatch")
    return rows


def build(secret: dict) -> tuple[dict, dict]:
    source_closure()
    raw_secret = secret_bytes(secret)
    old = read_json(SOURCE_GENERATION)
    old_qualification = read_json(SOURCE_QUALIFICATION)
    requests = read_json(REQUESTS)
    candidates = read_json(CANDIDATES)
    check_seal(old, "qualification_generation_identity")
    check_seal(old_qualification, "qualification_identity")
    candidate_core = dict(candidates)
    candidate_id = candidate_core.pop("manifest_identity", None)
    if candidate_id != digest(json.dumps(candidate_core, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()):
        raise ValueError("candidate object manifest seal mismatch")
    request_core = dict(requests)
    request_id = request_core.pop("request_manifest_identity", None)
    if request_id != digest(canonical(request_core)):
        raise ValueError("request manifest seal mismatch")
    if (old["alias_secret_commitment"] != HISTORICAL
            or old["request_manifest_identity"] != request_id
            or old["candidate_object_manifest_identity"] != candidate_id
            or old_qualification["qualification_generation_identity"] != old["qualification_generation_identity"]
            or old_qualification["request_manifest_identity"] != request_id
            or old_qualification["candidate_object_manifest_identity"] != candidate_id
            or len(requests["requests"]) != 200 or len(old["schedule"]) != 2400
            or old["candidate_execution_performed"] is not False
            or old["qualification_attempt_consumed"] is not False):
        raise ValueError("historical independent authority mismatch")
    case_ids = [row["case_id"] for row in requests["requests"]]
    new_schedule = schedule(case_ids, secret)
    if new_schedule == old["schedule"]:
        raise ValueError("successor schedule did not change")
    core = {k: v for k, v in old.items() if k != "qualification_generation_identity"}
    core.update(
        status="FROZEN_SUCCESSOR_V13_NEW_ALIAS_SECRET_PREINFERENCE",
        alias_secret_commitment=digest(raw_secret),
        schedule=new_schedule,
        schedule_lineage="NEW_SUCCESSOR_GENERATION_AFTER_LOST_V2_SECRET",
    )
    generation = sealed(core, "qualification_generation_identity")
    qualification_core = {k: v for k, v in old_qualification.items() if k != "qualification_identity"}
    qualification_core.update(
        status="PASS_SUCCESSOR_V13_OFFLINE_PREINFERENCE_ZERO_CANDIDATE_EXECUTION",
        qualification_generation_identity=generation["qualification_generation_identity"],
    )
    qualification_core["mechanism_source_sha256"] = {
        **old_qualification["mechanism_source_sha256"],
        "scripts/materialize_production_core_successor_qualification_generation_v13.py": digest(Path(__file__).read_bytes()),
    }
    qualification = sealed(qualification_core, "qualification_identity")
    return generation, qualification


def materialize(private_root: Path, backup_root: Path) -> dict[str, str]:
    if GENERATION.exists() or QUALIFICATION.exists():
        raise ValueError("successor public artifacts already exist")
    secret, commitment = create_secret(private_root, backup_root)
    generation, qualification = build(secret)
    for path, value in ((GENERATION, generation), (QUALIFICATION, qualification)):
        path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n")
    return {
        "alias_secret_commitment": commitment,
        "qualification_generation_identity": generation["qualification_generation_identity"],
        "qualification_identity": qualification["qualification_identity"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.private_root, args.backup_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
