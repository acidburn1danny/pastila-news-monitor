"""Consume exactly one Pilot 07 capability and freeze its observed result."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import ConstructorPacketCapabilityV1, prepare_development_constructor_access_v1
from pastila_scout.humor_batch2_development_constructor_v1 import construct_development_candidate_v1

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "3e49315afab444f3ab80f09ce63ffa327bc1031b"
EXECUTION_SOURCE_COMMIT = "5b864f19dc6f14561b5d8c59fe5d171d5af407e5"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-constructor-access-release-v3.json"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-construction-attempt01-v1.json"
ACCESS_SHA = "205b57f2817dde732942e963894569bc428e57d41fba830191ab52bfe5882bdb"
CONSTRUCTOR_SHA = "cad05554cae47782b6ced6c55a549bdb221de36035327fd9d82c2eaa02236eda"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 07 construction attempt already consumed")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != EXECUTION_SOURCE_COMMIT:
        raise SystemExit("HEAD differs from frozen execution source")
    access_path = ROOT / "src/pastila_scout/humor_batch2_constructor_access_v1.py"
    constructor_path = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v1.py"
    if hashlib.sha256(access_path.read_bytes()).hexdigest() != ACCESS_SHA:
        raise SystemExit("access source identity")
    if hashlib.sha256(constructor_path.read_bytes()).hexdigest() != CONSTRUCTOR_SHA:
        raise SystemExit("constructor source identity")
    release_bytes = subprocess.check_output(["git", "show", f"{RELEASE_COMMIT}:{RELEASE_PATH}"], cwd=ROOT)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    if prepared.release_identity != "74c25b8c033c1c0d65a2c1196a92bccf0d556785d4754308d604d321ff78f8fe":
        raise SystemExit("release identity")
    if prepared.packet_identity != "f52a1d542ddfb2ff10667dec1c22094132322500583ff39c07b80591e2dacdcf":
        raise SystemExit("packet identity")
    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    # Sole authorized constructor invocation. No code below may call it again.
    result = construct_development_candidate_v1(constructor_packet_bytes=packet_bytes)
    packet = json.loads(packet_bytes)
    candidate_bytes = result.candidate_surface_utf8 or b""
    if result.terminal_classification == "CANDIDATE_PRODUCED" and result.candidate_surface_utf8 is not None:
        candidate_bytes.decode("utf-8")
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY"
        candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT07_CANDIDATE_V1", {
            "constructor_packet_identity": prepared.packet_identity,
            "raw_surface_sha256": candidate_sha,
            "attempt_ordinal": 1,
            "partition": "DEVELOPMENT",
        })
        creative_family = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {
            "sealed_assignment_identity": packet["immutable_assignment_identity"],
            "source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"],
            "candidate_identity": candidate_id,
        })
        CANDIDATE.write_bytes(candidate_bytes)
    else:
        terminal, candidate_sha, candidate_id, creative_family = result.terminal_classification, None, None, "UNASSIGNED"
    forbidden = (b"HMCV1-", b"ABSURD_LOGICAL_EXTENSION", b"mechanism_id", b"mechanism_name", b"answer_key")
    hidden = any(token.lower() in candidate_bytes.lower() for token in forbidden)
    core = {
        "schema_name": "batch2-development-pilot07-construction-attempt01-v1",
        "schema_version": "1.0.0",
        "execution_source_commit": EXECUTION_SOURCE_COMMIT,
        "constructor_access_source_sha256": ACCESS_SHA,
        "constructor_source_sha256": CONSTRUCTOR_SHA,
        "release_commit": RELEASE_COMMIT,
        "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "selected_proposition_id": packet["selected_proposition_id"],
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1},
        "terminal_classification": terminal,
        "failure_code": result.failure_code,
        "candidate_identity": candidate_id,
        "candidate_surface_sha256": candidate_sha,
        "candidate_surface_byte_length": len(candidate_bytes) if candidate_bytes else None,
        "candidate_surface_present": result.candidate_surface_utf8 is not None,
        "candidate_partition": "DEVELOPMENT" if candidate_id else None,
        "creative_premise_family_id": creative_family,
        "construction_provenance": {
            "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"],
            "closed_authority_envelope_source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"],
            "obligation_instance_identity": packet["unlabeled_operational_obligation"]["obligation_instance_identity"],
        },
        "capability": {"single_use": True, "reads": 1, "consumed": True, "constructor_visible_sha256": result.constructor_visible_sha256},
        "constructor_exposure_reconciliation": {
            "authorized_packet_only": True,
            "exact_selected_source_span_only": True,
            "sealed_mapping_exposed": False,
            "blind_material_exposed": False,
            "repository_or_filesystem_access": False,
            "sibling_artifact_access": False,
            "environment_or_cli_access": False,
            "logs_or_telemetry_payload": False,
            "cache_or_temp_file_access": False,
            "process_handle_access": False,
            "network_access": False,
            "hidden_mechanism_metadata_introduced": hidden,
        },
        "post_construction_g02b_verdict": "PASS" if not hidden else "FAIL_HIDDEN_METADATA",
        "retry_authority": False,
        "repair_authority": False,
        "selection_authority": False,
        "authority_matrix": {key: False for key in ("owner_freeze", "mechanism_adjudication", "g04b_pool_certification", "model_training", "runtime_integration", "production_routing")},
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT07_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"terminal_classification": terminal, "candidate_identity": candidate_id,
                      "candidate_surface_sha256": candidate_sha, "creative_premise_family_id": creative_family,
                      "capability_consumed": True, "post_construction_g02b_verdict": evidence["post_construction_g02b_verdict"],
                      "evidence_identity": evidence["evidence_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
