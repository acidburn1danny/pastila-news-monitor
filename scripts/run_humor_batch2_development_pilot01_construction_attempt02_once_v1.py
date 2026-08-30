"""Run exactly one fresh source-bound Pilot 01 construction attempt."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import ConstructorPacketCapabilityV1, prepare_development_constructor_access_v1
from pastila_scout.humor_batch2_development_constructor_v1 import construct_development_candidate_v1

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "21ab740fa8bbf91e005713b2195cbde2ba041a6c"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-constructor-access-release-source-bound-v1.json"
PRIOR_EVIDENCE = "docs/artifacts/humor-mechanics-batch2-development-pilot01-construction-attempt01-v1.json"
SOURCE_MODULE = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v1.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-construction-attempt02-v1.json"
EXPECTED_CONSTRUCTOR_SOURCE_SHA256 = "5ad3cab4ec0a2ce0b975ea9866af41dff9454ed9b232d142e849ba2886106aa1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("fresh construction attempt already consumed")
    if hashlib.sha256(SOURCE_MODULE.read_bytes()).hexdigest() != EXPECTED_CONSTRUCTOR_SOURCE_SHA256:
        raise SystemExit("constructor source identity")
    prior = json.loads(subprocess.check_output(["git", "show", f"{RELEASE_COMMIT}^:{PRIOR_EVIDENCE}"], cwd=ROOT))
    if prior["attempt"]["consumed"] != 1 or prior["attempt"]["remaining"] != 0:
        raise SystemExit("prior attempt not exhausted")
    release_bytes = subprocess.check_output(["git", "show", f"{RELEASE_COMMIT}:{RELEASE_PATH}"], cwd=ROOT)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    # Sole fresh constructor invocation.
    result = construct_development_candidate_v1(constructor_packet_bytes=packet_bytes)
    if result.terminal_classification != "CANDIDATE_PRODUCED" or result.candidate_surface_utf8 is None:
        terminal = result.terminal_classification
        candidate_sha = None
        candidate_identity = None
        creative_family = "UNASSIGNED"
    else:
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY"
        candidate = result.candidate_surface_utf8
        candidate.decode("utf-8")
        candidate_sha = hashlib.sha256(candidate).hexdigest()
        candidate_identity = seal("B2_DEVELOPMENT_PILOT01_CANDIDATE_V1", {
            "constructor_packet_identity": prepared.packet_identity, "raw_surface_sha256": candidate_sha,
            "attempt_ordinal": 2, "partition": "DEVELOPMENT"})
        creative_family = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {
            "sealed_assignment_identity": json.loads(packet_bytes)["immutable_assignment_identity"],
            "source_commitment": json.loads(packet_bytes)["closed_factual_authority_envelope"]["source_commitment"],
            "candidate_identity": candidate_identity})
        CANDIDATE.write_bytes(candidate)
    packet = json.loads(packet_bytes)
    candidate_bytes = result.candidate_surface_utf8 or b""
    forbidden = (b"HMCV1-", b"ABSURD_LOGICAL_EXTENSION", b"mechanism_id", b"mechanism_name", b"answer_key")
    hidden_metadata = any(token.lower() in candidate_bytes.lower() for token in forbidden)
    core = {
        "schema_name": "batch2-development-pilot01-construction-attempt02-v1", "schema_version": "1.0.0",
        "execution_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "constructor_source_sha256": EXPECTED_CONSTRUCTOR_SOURCE_SHA256,
        "release_commit": RELEASE_COMMIT, "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "prior_attempt_evidence_identity": prior["evidence_identity"], "prior_attempt_reused": False,
        "fresh_attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1},
        "terminal_classification": terminal, "failure_code": result.failure_code,
        "candidate_identity": candidate_identity, "candidate_surface_sha256": candidate_sha,
        "candidate_surface_byte_length": len(candidate_bytes) if candidate_bytes else None,
        "candidate_surface_present": result.candidate_surface_utf8 is not None,
        "candidate_partition": "DEVELOPMENT" if candidate_identity else None,
        "creative_premise_family_id": creative_family,
        "construction_provenance": {"source_sha256": packet["source_object"]["sha256"],
                                    "source_git_blob_oid_sha1": packet["source_object"]["git_blob_oid_sha1"],
                                    "closed_authority_envelope_source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"],
                                    "operational_obligation_id": packet["unlabeled_operational_obligation"]["obligation_id"]},
        "capability": {"single_use": True, "reads": 1, "consumed": True,
                       "constructor_visible_sha256": result.constructor_visible_sha256},
        "constructor_exposure_reconciliation": {
            "authorized_packet_only": True, "exact_source_bytes_only": True,
            "sealed_mapping_exposed": False, "blind_material_exposed": False,
            "repository_or_filesystem_access": False, "sibling_artifact_access": False,
            "environment_or_cli_access": False, "logs_or_telemetry_payload": False,
            "cache_or_temp_file_access": False, "process_handle_access": False,
            "hidden_mechanism_metadata_introduced": hidden_metadata,
        },
        "post_construction_g02b_verdict": "PASS" if not hidden_metadata else "FAIL_HIDDEN_METADATA",
        "retry_authority": False, "repair_authority": False, "selection_authority": False,
        "authority_matrix": {key: False for key in ("owner_freeze", "mechanism_adjudication", "model_training",
                                                     "runtime_integration", "production_routing")},
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTION_ATTEMPT02_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps({"terminal_classification": terminal, "candidate_identity": candidate_identity,
                      "candidate_surface_sha256": candidate_sha, "creative_premise_family_id": creative_family,
                      "capability_consumed": True, "post_construction_g02b_verdict": evidence["post_construction_g02b_verdict"],
                      "evidence_identity": evidence["evidence_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
