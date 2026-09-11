"""Bind the V5 candidates to the frozen Core V2 schedule without redraw."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
SECRET = ROOT / ".pastila-runtime/production-core-successor-qualification-v5/candidate-alias-secret-v5.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def seal(core: dict[str, object], field: str) -> dict[str, object]:
    return {**core, field: hashlib.sha256(canonical(core)).hexdigest()}


def load(name: str) -> dict[str, object]:
    path = ART / name
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"authority input rejected: {name}")
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise SystemExit(f"object required: {name}")
    return value


def write(name: str, value: object) -> None:
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    path = ART / name
    if path.exists() and (path.is_symlink() or path.read_bytes() != encoded):
        raise SystemExit(f"published artifact differs: {name}")
    if not path.exists():
        path.write_bytes(encoded)


def main() -> int:
    old_generation = load("production-core-successor-comparative-qualification-generation-v3.json")
    old_qualification = load("production-core-successor-candidate-generation-qualification-v3.json")
    candidate = load("production-core-successor-candidate-object-manifest-v5.json")
    candidate_core = dict(candidate)
    candidate_identity = candidate_core.pop("manifest_identity", None)
    candidate_bytes = json.dumps(candidate_core, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()
    if candidate_identity != "7bff8d58e56c1fd8e29f91f440b4f4c91ce4d79413d4186d895406f852c6abf9" or hashlib.sha256(candidate_bytes).hexdigest() != candidate_identity:
        raise SystemExit("V5 candidate manifest identity mismatch")
    predecessor_secret = json.loads((ROOT / ".pastila-runtime/production-core-successor-qualification-v3/candidate-alias-secret-v3.json").read_bytes())
    successor_secret = {**predecessor_secret, "aliases": {alias: ("pastila-editor-core-v1.1-json-successor-v2" if name == "pastila-editor-core-v1.1-json-successor" else name) for alias, name in predecessor_secret["aliases"].items()}}
    secret_bytes = canonical(successor_secret)
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    if SECRET.exists():
        if SECRET.is_symlink() or SECRET.read_bytes() != secret_bytes:
            raise SystemExit("V5 alias secret substitution")
    else:
        descriptor = os.open(SECRET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, secret_bytes)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    generation_core = {k: v for k, v in old_generation.items() if k != "qualification_generation_identity"}
    generation_core.update(status="FROZEN_SUCCESSOR_V5_PREINFERENCE_CANDIDATE_NEUTRAL", candidate_object_manifest_identity=candidate_identity, alias_secret_commitment=hashlib.sha256(secret_bytes).hexdigest(), schedule_lineage="PREDECESSOR_ORDER_PRESERVED_NO_REDRAW", qualification_attempt_consumed=False, candidate_execution_performed=False, retry_or_redraw_authorized=False, promotion_effect=False)
    generation = seal(generation_core, "qualification_generation_identity")
    qualification_core = {k: v for k, v in old_qualification.items() if k != "qualification_identity"}
    qualification_core.update(status="PASS_SUCCESSOR_V5_OFFLINE_PREINFERENCE_ZERO_CANDIDATE_EXECUTION", qualification_generation_identity=generation["qualification_generation_identity"], candidate_object_manifest_identity=candidate_identity, qualification_attempt_consumed=False, candidate_execution_performed=False, adjudication_performed=False, promotion_effect=False)
    qualification = seal(qualification_core, "qualification_identity")
    write("production-core-successor-comparative-qualification-generation-v5.json", generation)
    write("production-core-successor-candidate-generation-qualification-v5.json", qualification)
    print(generation["qualification_generation_identity"])
    print(qualification["qualification_identity"])
    print(hashlib.sha256(secret_bytes).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
