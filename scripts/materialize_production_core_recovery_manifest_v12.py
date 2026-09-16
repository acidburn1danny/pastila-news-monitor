"""Materialize the strict clean-recovery manifest for the published V12 checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pastila_scout.production_core_recovery_v12 import seal, validate


def build() -> dict[str, object]:
    core: dict[str, object] = {
        "schema": "pastila-production-core-v12-clean-recovery",
        "schema_version": 1,
        "status": "PENDING_SECURE_PRIVATE_KEY_BACKUP",
        "repository": {
            "remote": "https://github.com/acidburn1danny/pastila-news-monitor.git",
            "canonical_branch": "successor/core-v2-v12-runner-binding-remediation",
            "source_checkpoint": {
                "commit": "2c64de10398fe39cbd42d7f2d46d544e5ac0fe3f",
                "tree": "3c83e9901cbc743f0b83feeeab19e5724206b977",
            },
            "recovery_metadata_rule": "checkout the published branch head; source checkpoint must be an ancestor",
        },
        "v12": {
            "runner_identity": "b7073a3b75036e5be26aa4b1d9546aa9f012370168a74df552b648708e399e29",
            "next_action": "Build and audit the successor execution authority binding the canonical V12 recovery commit and runner V12 identity, with candidate execution and attempt consumption still zero.",
        },
        "execution_state": {
            "successor_authority_built": False,
            "candidate_execution": 0,
            "successor_attempt_consumption": 0,
            "adjudication": False,
            "promotion": False,
        },
        "active_identities": {
            "qualification_generation": "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7",
            "candidate_manifest": "6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314",
            "adapter_audit": "50eb1fb7b425fdee07b7fbd672c405c0dc2cd5b34e0df6270bb0468c3ea846d8",
            "training_runtime_authority": "cda69071c31cacd50cd6ace67fa7c7955df431ad6f0ad9035d12a7df414e3d7b",
        },
        "external_objects": [
            {
                "logical_name": "base-model",
                "backup_name": "base-model-f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39.tar",
                "archive_sha256": "8138a2e11a94c65b4291501f1efba1dd28f5d808060b88a3636a7037c95ab0d9",
                "archive_bytes": 27924418560,
                "flat_content_identity": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
                "content_files": 17,
                "content_bytes": 27924394330,
            },
            {
                "logical_name": "inference-rootfs",
                "backup_name": "rootfs-274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4.tar",
                "archive_sha256": "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
                "archive_bytes": 11113052160,
            },
            {
                "logical_name": "tokenizer",
                "backup_name": "tokenizer-2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c.tar",
                "archive_sha256": "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c",
                "archive_bytes": 17295360,
            },
            {
                "logical_name": "adapter-v10-v1.1",
                "backup_name": "adapter-813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32.tar",
                "archive_sha256": "0e6cfe05dadf983eecd799c86245892a6591fa653e10f209e917b011afcea268",
                "archive_bytes": 243896320,
                "flat_content_identity": "813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32",
                "content_files": 4,
                "content_bytes": 243885915,
            },
            {
                "logical_name": "adapter-v10-v1.2",
                "backup_name": "adapter-8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f.tar",
                "archive_sha256": "c85c60c60b5c30e57df309d1c1cf3c4580a3507bb09753e5705c74ba264eab22",
                "archive_bytes": 243896320,
                "flat_content_identity": "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f",
                "content_files": 4,
                "content_bytes": 243885853,
            },
        ],
        "secret_recovery": {
            "private_key_committed": False,
            "requirement": "securely back up or explicitly rotate the V8.1 Ed25519 private key; rotation changes future signatures but must not rewrite historical bindings",
            "public_material_is_versioned": True,
        },
        "platform": {
            "windows": "Windows 11 with WSL2",
            "wsl_distribution": "Ubuntu-24.04",
            "gpu": "RTX 5080 with a compatible WSL NVIDIA driver",
            "python": "3.14 project environment from pyproject.toml",
            "minimum_free_bytes_for_external_restore": 40000000000,
        },
        "classification": {
            "KEEP_AND_VERSION": ["source", "schemas", "materializers", "manifests", "receipts", "audit/disposition/addendum provenance"],
            "KEEP_EXTERNAL_WITH_REPRODUCIBLE_BINDING": ["base model", "inference rootfs", "tokenizer", "two final V10 adapters"],
            "ARCHIVE": ["historical evidence already sealed and versioned"],
            "SAFE_TO_DELETE": ["reproducible caches", "superseded materializations", "accepted-checkpoint duplicates", "test temp directories"],
            "UNKNOWN_BLOCKER": ["V8.1 Ed25519 private key secure backup destination"],
        },
        "remaining_blockers": ["V8.1_ED25519_PRIVATE_KEY_HAS_NO_VERIFIED_OFF_SYSTEM_ENCRYPTED_BACKUP"],
    }
    result = seal(core)
    validate(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    raw = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if options.output.exists() and options.output.read_bytes() != raw:
        raise SystemExit("published recovery manifest differs")
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_bytes(raw)
    print(build()["recovery_manifest_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
