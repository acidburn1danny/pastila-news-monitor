"""Freeze the successor candidate objects into the unchanged Core V2 matrix."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
SECRET = (
    ROOT
    / ".pastila-runtime/production-core-successor-qualification-v3/candidate-alias-secret-v3.json"
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def seal(core: dict[str, object], field: str) -> dict[str, object]:
    return {**core, field: hashlib.sha256(canonical(core)).hexdigest()}


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_bytes())
    if not isinstance(value, dict):
        raise SystemExit(f"{name}: object required")
    return value


def write(name: str, value: object) -> None:
    (ART / name).write_bytes(
        json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )


def main() -> int:
    old_generation = load(
        "production-core-comparative-qualification-generation-v2.json"
    )
    old_qualification = load(
        "production-core-candidate-generation-qualification-v2.json"
    )
    runtime = load("production-core-training-runtime-authority-v1.json")
    predecessor_secret = json.loads(
        (
            ROOT
            / ".pastila-runtime/production-core-qualification-v2/candidate-alias-secret-v2.json"
        ).read_bytes()
    )
    successor_secret = {
        **predecessor_secret,
        "aliases": {
            alias: str(candidate).replace("-experimental", "-json-successor")
            for alias, candidate in predecessor_secret["aliases"].items()
        },
    }
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    secret_bytes = canonical(successor_secret)
    if SECRET.exists():
        if SECRET.is_symlink() or SECRET.read_bytes() != secret_bytes:
            raise SystemExit("successor alias secret substitution")
    else:
        descriptor = os.open(SECRET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, secret_bytes)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    successor_commitment = hashlib.sha256(secret_bytes).hexdigest()
    candidate_core = {
        "schema": "pastila-production-core-candidate-object-manifest",
        "schema_version": 3,
        "status": "SUCCESSOR_CONTENT_ADDRESSED_AUTHORITY_NO_EXECUTION",
        "base_model_manifest_sha256": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
        "tokenizer_sha256": "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c",
        "tokenizer_fix_mistral_regex": True,
        "adapter_manifest_sha256": {
            "pastila-editor-core-v1.1-json-successor": "16d6384355abfeff9a2c35cfa9866c604f8fd9703c19dcfbefcfdbb7fdb7dcf3",
            "pastila-editor-core-v1.2-json-successor": "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719",
        },
        "training_receipt_identity": {
            "pastila-editor-core-v1.1-json-successor": "cab8806ae4b8a78cf355ebc065f60cdf19fc13b6a37adefe47482ab7751e0e77",
            "pastila-editor-core-v1.2-json-successor": "d362ab7d26e0bbb9793782ca294376b248de053fc3dbe4fc5740359cfdbf2acf",
        },
        "training_runtime_authority_identity": runtime[
            "training_runtime_authority_identity"
        ],
        "predecessor_terminal_disposition_identity": "acd5b874de1a3b9c638194836d94f6f7b569781c2b63f778b04c8cb44871084f",
        "rootfs_sha256": "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    candidate = seal(candidate_core, "manifest_identity")
    generation_core = {
        k: v
        for k, v in old_generation.items()
        if k != "qualification_generation_identity"
    }
    generation_core["status"] = "FROZEN_SUCCESSOR_PREINFERENCE_CANDIDATE_NEUTRAL"
    generation_core["candidate_object_manifest_identity"] = candidate[
        "manifest_identity"
    ]
    generation_core["alias_secret_commitment"] = successor_commitment
    generation_core["schedule_lineage"] = "PREDECESSOR_ORDER_PRESERVED_NO_REDRAW"
    generation_core["qualification_attempt_consumed"] = False
    generation = seal(generation_core, "qualification_generation_identity")
    qualification_core = {
        k: v for k, v in old_qualification.items() if k != "qualification_identity"
    }
    qualification_core["status"] = (
        "PASS_SUCCESSOR_OFFLINE_PREINFERENCE_ZERO_CANDIDATE_EXECUTION"
    )
    qualification_core["qualification_generation_identity"] = generation[
        "qualification_generation_identity"
    ]
    qualification_core["candidate_object_manifest_identity"] = candidate[
        "manifest_identity"
    ]
    qualification_core["qualification_attempt_consumed"] = False
    qualification_core["adjudication_performed"] = False
    qualification = seal(qualification_core, "qualification_identity")
    write("production-core-successor-candidate-object-manifest-v3.json", candidate)
    write(
        "production-core-successor-comparative-qualification-generation-v3.json",
        generation,
    )
    write(
        "production-core-successor-candidate-generation-qualification-v3.json",
        qualification,
    )
    source_paths = (
        "docs/schemas/production-core-candidate-execution-authority-v3.schema.json",
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
    execution_core = {
        "schema": "pastila-production-core-candidate-execution-authority",
        "schema_version": 2,
        "status": "PASS_OFFLINE_EXECUTION_AUTHORITY_ZERO_ATTEMPTS",
        "authority_identities": {
            "qualification_generation_identity": generation[
                "qualification_generation_identity"
            ],
            "qualification_identity": qualification["qualification_identity"],
            "request_manifest_identity": generation["request_manifest_identity"],
            "candidate_object_manifest_identity": candidate["manifest_identity"],
        },
        "source_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in source_paths
        },
        "matrix_rows": 2400,
        "attempt_ordinal": 1,
        "retry_or_redraw_authorized": False,
        "adjudication_performed": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    execution = seal(execution_core, "execution_authority_identity")
    write("production-core-candidate-execution-authority-v3.json", execution)
    print(candidate["manifest_identity"])
    print(generation["qualification_generation_identity"])
    print(qualification["qualification_identity"])
    print(execution["execution_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
