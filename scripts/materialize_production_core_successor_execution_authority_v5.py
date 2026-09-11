"""Freeze the audited V5 qualification execution authority with zero attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BOUND_COMMIT = "040122150a62cd08861dbec02f9085f7e521c784"
SOURCE_PATHS = (
    "docs/schemas/production-core-candidate-execution-authority-v5.schema.json",
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/materialize_production_core_successor_candidate_manifest_v5.py",
    "scripts/materialize_production_core_successor_qualification_generation_v5.py",
    "scripts/execute_production_core_candidate_qualification_v3.py",
    "scripts/launch_production_core_candidate_qualification_v3.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v3.sh",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
    "tests/test_production_core_successor_execution_authority_v3.py",
    "tests/test_production_core_successor_candidate_manifest_v5.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load(name: str, field: str, expected: str, *, sorted_keys: bool = False) -> dict[str, object]:
    path = ART / name
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"authority input rejected: {name}")
    value = json.loads(path.read_bytes())
    core = dict(value)
    claimed = core.pop(field, None)
    observed = hashlib.sha256(json.dumps(core, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=sorted_keys).encode()).hexdigest()
    if claimed != expected or observed != expected:
        raise SystemExit(f"authority identity mismatch: {name}")
    return value


def build() -> dict[str, object]:
    generation = load("production-core-successor-comparative-qualification-generation-v5.json", "qualification_generation_identity", "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d")
    qualification = load("production-core-successor-candidate-generation-qualification-v5.json", "qualification_identity", "4d2a4b7a42141668e907bd90cb96cf8d28dce518761b3c0dc0375954ea6575f4")
    candidates = load("production-core-successor-candidate-object-manifest-v5.json", "manifest_identity", "7bff8d58e56c1fd8e29f91f440b4f4c91ce4d79413d4186d895406f852c6abf9", sorted_keys=True)
    audit = load("production-core-v1.1-successor-adapter-audit-receipt-v5.json", "adapter_audit_identity", "7519871ebd5cc566a06a8c24f04976244cda9e0653e35464adc1ef8bd80b77a2", sorted_keys=True)
    for value in (generation, qualification, candidates, audit):
        if value.get("candidate_execution_performed") is not False or value.get("qualification_attempt_consumed") is not False or value.get("promotion_effect") is not False:
            raise SystemExit("non-zero qualification lineage state")
    for relative in SOURCE_PATHS:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"source path rejected: {relative}")
    core = {
        "schema": "pastila-production-core-candidate-execution-authority",
        "schema_version": 5,
        "status": "FROZEN_SUCCESSOR_V5_EXECUTION_AUTHORITY_ZERO_ATTEMPTS_OWNER_EXECUTION_NOT_AUTHORIZED",
        "bound_source_commit": BOUND_COMMIT,
        "authority_identities": {
            "qualification_generation_identity": generation["qualification_generation_identity"],
            "qualification_identity": qualification["qualification_identity"],
            "request_manifest_identity": generation["request_manifest_identity"],
            "candidate_object_manifest_identity": candidates["manifest_identity"],
            "candidate_audit_receipt_identity": audit["adapter_audit_identity"],
        },
        "source_sha256": {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in SOURCE_PATHS},
        "matrix_rows": 2400,
        "attempt_ordinal": 1,
        "attempt_consumption_authorized": False,
        "candidate_execution_authorized": False,
        "retry_or_redraw_authorized": False,
        "adjudication_performed": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    return {**core, "execution_authority_identity": identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = build()
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    if args.output.exists() and (args.output.is_symlink() or args.output.read_bytes() != encoded):
        raise SystemExit("published authority differs")
    if not args.output.exists():
        args.output.write_bytes(encoded)
    print(value["execution_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
