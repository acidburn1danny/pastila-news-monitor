"""Consume the single Pilot 01 construction attempt and freeze exact evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import (
    ConstructorPacketCapabilityV1,
    prepare_development_constructor_access_v1,
)
from pastila_scout.humor_batch2_development_constructor_v1 import construct_development_candidate_v1

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "81b6e690843b29139f6b199f3be8904a5e613b93"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-constructor-access-release-v1.json"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-construction-attempt01-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD differs from G02B release commit")
    if EVIDENCE.exists():
        raise SystemExit("construction attempt already consumed")
    release_bytes = subprocess.check_output(["git", "show", f"{COMMIT}:{RELEASE_PATH}"], cwd=ROOT)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    # Sole constructor invocation.
    result = construct_development_candidate_v1(constructor_packet_bytes=packet_bytes)
    if result.candidate_surface_utf8 is not None:
        raise SystemExit("unexpected candidate path not authorized by this constructor version")
    core = {
        "schema_name": "batch2-development-pilot01-construction-attempt-v1", "schema_version": "1.0.0",
        "g02b_commit": COMMIT, "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1},
        "terminal_classification": result.terminal_classification, "failure_code": result.failure_code,
        "candidate_identity": None, "candidate_surface_sha256": None, "candidate_surface_present": False,
        "creative_premise_family_id": "UNASSIGNED",
        "capability": {"single_use": True, "reads": 1, "consumed": True,
                       "constructor_visible_sha256": result.constructor_visible_sha256},
        "constructor_exposure_reconciliation": {
            "authorized_packet_only": True, "sealed_mapping_exposed": False, "blind_material_exposed": False,
            "repository_or_filesystem_access": False, "sibling_artifact_access": False,
            "environment_or_cli_access": False, "logs_or_telemetry_payload": False,
            "cache_or_temp_file_access": False, "process_handle_access": False,
            "hidden_mechanism_metadata_introduced": False,
        },
        "post_construction_g02b_verdict": "PASS_EXPOSURE_RECONCILIATION_TECHNICAL_FAILURE_NO_CANDIDATE",
        "retry_authority": False, "repair_authority": False,
        "authority_matrix": {key: False for key in ("owner_freeze", "mechanism_adjudication", "model_training",
                                                     "runtime_integration", "production_routing")},
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({"terminal_classification": result.terminal_classification,
                      "failure_code": result.failure_code, "attempt_consumed": "1/1",
                      "candidate_identity": None, "creative_premise_family_id": "UNASSIGNED",
                      "post_construction_g02b_verdict": evidence["post_construction_g02b_verdict"],
                      "evidence_identity": evidence["evidence_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
