"""Freeze the remediated successor execution boundary with zero new attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUND_COMMIT = "6c72a3c45c4a251a8fe61db82aea5bd462238120"
SOURCE_PATHS = (
    "docs/schemas/production-core-candidate-execution-authority-v4.schema.json",
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/execute_production_core_candidate_qualification_v3.py",
    "scripts/launch_production_core_candidate_qualification_v3.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "scripts/run_production_core_candidate_qualification_v3.sh",
    "src/pastila_scout/production_core_candidate_execution_authority_v3.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v3.py",
    "src/pastila_scout/production_core_semantic_authority_v2.py",
    "tests/test_production_core_successor_execution_authority_v3.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_artifact(name: str, identity_field: str, expected: str) -> dict[str, object]:
    path = ROOT / "docs/artifacts" / name
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"authority input rejected: {name}")
    value = json.loads(path.read_bytes())
    core = dict(value)
    if core.pop(identity_field, None) != expected or identity(core) != expected:
        raise SystemExit(f"authority identity mismatch: {name}")
    return value


def build() -> dict[str, object]:
    generation = load_artifact(
        "production-core-successor-comparative-qualification-generation-v3.json",
        "qualification_generation_identity",
        "7b4900523953253391e8753d39ae8253e6652055cf5c99612a007eaadba552f9",
    )
    qualification = load_artifact(
        "production-core-successor-candidate-generation-qualification-v3.json",
        "qualification_identity",
        "281f5cfd3e5627e582e099129ad8b023052b694e5834f6b6843b13368abbc314",
    )
    candidates = load_artifact(
        "production-core-successor-candidate-object-manifest-v3.json",
        "manifest_identity",
        "94ce74f28df6027c404800787e7ba39c16a35f688094c2bb96220d1592ad72ce",
    )
    addendum = load_artifact(
        "production-core-successor-root-cause-addendum-v3.json",
        "addendum_identity",
        "5290e19dae6d775d03200629b98980823a43495da607cf952286d2a052ed7672",
    )
    if (
        generation.get("candidate_execution_performed") is not False
        or generation.get("qualification_attempt_consumed") is not False
        or qualification.get("candidate_execution_performed") is not False
        or qualification.get("qualification_attempt_consumed") is not False
        or candidates.get("candidate_execution_performed") is not False
        or addendum.get("attempt_consumed_permanently") is not True
        or addendum.get("retry_or_redraw") is not False
        or addendum.get("adjudication_performed") is not False
        or addendum.get("promotion_effect") is not False
    ):
        raise SystemExit("successor lineage state mismatch")
    for relative in SOURCE_PATHS:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"source path rejected: {relative}")
    core = {
        "schema": "pastila-production-core-candidate-execution-authority",
        "schema_version": 4,
        "status": "FROZEN_SUCCESSOR_EXECUTION_AUTHORITY_ZERO_ATTEMPTS_OWNER_EXECUTION_NOT_AUTHORIZED",
        "bound_source_commit": BOUND_COMMIT,
        "predecessor_attempt_identity": "337bb8acc130cc02f77f83c7a026b9212c781ba06d11989e64ef11b334f6a5ca",
        "predecessor_attempt_consumed_permanently": True,
        "authority_identities": {
            "qualification_generation_identity": generation[
                "qualification_generation_identity"
            ],
            "qualification_identity": qualification["qualification_identity"],
            "request_manifest_identity": generation["request_manifest_identity"],
            "candidate_object_manifest_identity": candidates["manifest_identity"],
            "root_cause_addendum_identity": addendum["addendum_identity"],
        },
        "source_sha256": {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in SOURCE_PATHS
        },
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
    if args.output.exists() and args.output.read_bytes() != encoded:
        raise SystemExit("published authority differs")
    if not args.output.exists():
        args.output.write_bytes(encoded)
    print(value["execution_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
