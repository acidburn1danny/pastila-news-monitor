"""Freeze V6 checkpoint/resume authority without consuming an attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE_PATHS = (
    "docs/schemas/production-core-candidate-execution-authority-v6.schema.json",
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/execute_production_core_candidate_qualification_v3.py",
    "scripts/launch_production_core_candidate_qualification_v3.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v3.sh",
    "scripts/materialize_production_core_successor_execution_authority_v6.py",
    "scripts/smoke_production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
    "tests/test_production_core_checkpoint_resume_v6.py",
    "tests/test_production_core_successor_execution_authority_v3.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def build() -> dict[str, object]:
    core = {
        "schema": "pastila-production-core-candidate-execution-authority", "schema_version": 6,
        "status": "FROZEN_SUCCESSOR_V6_CHECKPOINT_RESUME_AUTHORITY_ZERO_ATTEMPTS_OWNER_EXECUTION_NOT_AUTHORIZED",
        "bound_source_commit": "cb10ec438e2189067d1340dc9e357d4f2069f60b",
        "authority_identities": {
            "qualification_generation_identity": "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d",
            "qualification_identity": "4d2a4b7a42141668e907bd90cb96cf8d28dce518761b3c0dc0375954ea6575f4",
            "request_manifest_identity": "f3b0e0d11c5b73fba39ce21f5daa040e788a2ea09d455389bf990ee8264b4d03",
            "candidate_object_manifest_identity": "7bff8d58e56c1fd8e29f91f440b4f4c91ce4d79413d4186d895406f852c6abf9",
            "candidate_audit_receipt_identity": "7519871ebd5cc566a06a8c24f04976244cda9e0653e35464adc1ef8bd80b77a2",
        },
        "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS},
        "matrix_rows": 2400,
        "checkpoint_policy": {"checkpoint_count": 12, "rows_per_checkpoint": 200, "atomic_publish": True, "content_addressed_receipt": True, "same_attempt_resume_only": True, "recalculate_finalized_rows": False},
        "attempt_ordinal": 1, "attempt_consumption_authorized": False,
        "candidate_execution_authorized": False, "retry_or_redraw_authorized": False,
        "adjudication_performed": False, "candidate_execution_performed": False, "promotion_effect": False,
    }
    return {**core, "execution_authority_identity": identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = build()
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    if args.output.exists() and (args.output.is_symlink() or args.output.read_bytes() != encoded):
        raise SystemExit("published V6 authority differs")
    if not args.output.exists():
        args.output.write_bytes(encoded)
    print(value["execution_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
