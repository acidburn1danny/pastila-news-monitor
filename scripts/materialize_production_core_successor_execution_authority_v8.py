"""Freeze V8 lifecycle-schema repair authority with zero attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUND_COMMIT = "5d51f5fbe403803fcbf89fe535803438a4ae4e33"
PREDECESSOR_FAILURE = "a4eb2c19c9b47a74236793adc01cd807d4ed5048415407095737553a12185fc6"
PREDECESSOR_ADDENDUM = "06661c7dc7c73d80bfef026da13e50732de27eb2f19cc3d4ad674e3ede44f84d"
SOURCE_PATHS = (
    "docs/schemas/production-core-candidate-execution-authority-v8.schema.json",
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/execute_production_core_candidate_qualification_v3.py",
    "scripts/launch_production_core_candidate_qualification_v3.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v3.sh",
    "scripts/materialize_production_core_successor_execution_authority_v8.py",
    "scripts/smoke_production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
    "tests/test_production_core_checkpoint_resume_v6.py",
    "tests/test_production_core_successor_execution_authority_v3.py",
)
FROZEN_SOURCE_SHA256 = {
    "docs/schemas/production-core-candidate-execution-authority-v8.schema.json": "a546bf0de0dbd6902cd307e72b5e4f4741b4680ff28435eff104f1c0ba581232",
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json": "55abaf7d8fc8a0ebd1b9b3db3d5e213b6e36534ff078a3687de80b6cc246cd33",
    "scripts/execute_production_core_candidate_qualification_v3.py": "5e873f291da0c861bf55355ad522b87dd06e276d17d9b290092aa3c8556ab9f7",
    "scripts/launch_production_core_candidate_qualification_v3.py": "a2f6572698d21a531a6b126f70d52c4ffb2151444f4c8a3eb50b7513ca365e60",
    "scripts/resolve_production_core_object_authority_v2.sh": "4231ea3dae2f9399edeed8c2d5f96faa16c13714a594a1a381ea50ceb4cf0be0",
    "scripts/run_production_core_candidate_qualification_v3.sh": "74d57b5c89c32792fee22eb2ac5b3206008577a2becccaa318d0f0fc90878e43",
    "scripts/materialize_production_core_successor_execution_authority_v8.py": "be6f4caf6baacf513589af83ba6528f95650022503462dc4f7abfaa75c746749",
    "scripts/smoke_production_core_checkpoint_resume_v6.py": "4a18addcb533705337ed08890c0002712ccafe6e69ab0711adaab3573422340b",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py": "680db18a94b61327d0285f1e4ff04bb60b9b4e0dbc601145511dcf97b8e6c4d8",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py": "2d211a17bb6d10bea87d30c296f23c5a9c791d82e764d93e6eb178777ead51fc",
    "src/pastila_scout/production_core_checkpoint_resume_v6.py": "d33e08722a0f4759644cd6b1e902570ec430202bfe6a7c1f2c269fbc722b8d58",
    "src/pastila_scout/production_core_semantic_authority_v2.py": "af079fb50f281e09433dba299feaf9c2354bb4946df8e476658f71cc228d4c41",
    "tests/test_production_core_checkpoint_resume_v6.py": "aae8ad8195bf4ab75a0cffb68de088a6315146959b7a678b4bc64b1d1118af60",
    "tests/test_production_core_successor_execution_authority_v3.py": "9e6137662260ba834e08ec5d954560247175f65e04fb8ab54c7f52885db99711",
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def build() -> dict[str, object]:
    core = {
        "schema": "pastila-production-core-candidate-execution-authority",
        "schema_version": 8,
        "status": "FROZEN_SUCCESSOR_V8_LIFECYCLE_SCHEMA_REPAIR_ZERO_ATTEMPTS",
        "bound_source_commit": BOUND_COMMIT,
        "predecessor_terminal_failure_identity": PREDECESSOR_FAILURE,
        "predecessor_root_cause_addendum_identity": PREDECESSOR_ADDENDUM,
        "authority_identities": {
            "qualification_generation_identity": "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d",
            "qualification_identity": "4d2a4b7a42141668e907bd90cb96cf8d28dce518761b3c0dc0375954ea6575f4",
            "request_manifest_identity": "f3b0e0d11c5b73fba39ce21f5daa040e788a2ea09d455389bf990ee8264b4d03",
            "candidate_object_manifest_identity": "7bff8d58e56c1fd8e29f91f440b4f4c91ce4d79413d4186d895406f852c6abf9",
            "candidate_audit_receipt_identity": "7519871ebd5cc566a06a8c24f04976244cda9e0653e35464adc1ef8bd80b77a2",
        },
        # Historical authorities reproduce the hashes at their bound commit;
        # successor edits must not reinterpret their immutable closure.
        "source_sha256": dict(FROZEN_SOURCE_SHA256),
        "matrix_rows": 2400,
        "checkpoint_policy": {
            "checkpoint_count": 12,
            "rows_per_checkpoint": 200,
            "ordinal_source": "VALIDATED_AUTHORITY_SCHEDULE",
            "atomic_publish": True,
            "content_addressed_receipt": True,
            "same_attempt_resume_only": True,
            "recalculate_finalized_rows": False,
        },
        "lifecycle_completed_contract": {
            "termination_reason_required": True,
            "termination_reason_observation_binding_required": True,
            "missing_wrong_or_extra_fields_rejected": True,
        },
        "attempt_ordinal": 1,
        "attempt_consumption_authorized": False,
        "candidate_execution_authorized": False,
        "retry_or_redraw_authorized": False,
        "adjudication_performed": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    return {
        **core,
        "execution_authority_identity": hashlib.sha256(canonical(core)).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = build()
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    if args.output.exists() and (
        args.output.is_symlink() or args.output.read_bytes() != raw
    ):
        raise SystemExit("published V8 authority differs")
    if not args.output.exists():
        args.output.write_bytes(raw)
    print(value["execution_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
