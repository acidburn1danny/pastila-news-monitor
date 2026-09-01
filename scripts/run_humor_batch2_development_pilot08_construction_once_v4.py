"""Consume exactly one Pilot 08 capability and freeze its observed result."""

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
from pastila_scout.humor_batch2_development_constructor_v4 import (
    construct_development_candidate_v4,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "c33e82cac589b0fdf036331f7bf6cec97fe75106"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-constructor-access-release-v4.json"
IMPLEMENTATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v4.json"
DENYSET_PATH = "docs/artifacts/humor-mechanics-batch2-nonblind-development-fragment-denyset-v4.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot08_construction_once_v4.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-construction-attempt01-v1.json"
ACCESS_SHA = "4663c06075eb5bfe87e59b9530e834c26a35ac23670cd02a8b235f960282f72e"
CONSTRUCTOR_SHA = "f13136099e75c95033a54aabb447ded743c96a55479dc9a8b685f2a2b41c12d7"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 08 construction attempt already consumed")
    execution_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not subprocess.run(["git", "merge-base", "--is-ancestor", RELEASE_COMMIT, execution_commit], cwd=ROOT).returncode == 0:
        raise SystemExit("release commit is not an ancestor")
    runner = (ROOT / RUNNER_PATH).read_bytes()
    if committed(execution_commit, RUNNER_PATH) != runner:
        raise SystemExit("runner is not exact committed execution source")
    access = (ROOT / "src/pastila_scout/humor_batch2_constructor_access_v1.py").read_bytes()
    constructor = (ROOT / "src/pastila_scout/humor_batch2_development_constructor_v4.py").read_bytes()
    if hashlib.sha256(access).hexdigest() != ACCESS_SHA or committed(execution_commit, "src/pastila_scout/humor_batch2_constructor_access_v1.py") != access:
        raise SystemExit("access source identity")
    if hashlib.sha256(constructor).hexdigest() != CONSTRUCTOR_SHA or committed(execution_commit, "src/pastila_scout/humor_batch2_development_constructor_v4.py") != constructor:
        raise SystemExit("constructor source identity")
    implementation = json.loads(committed(execution_commit, IMPLEMENTATION_PATH))
    denyset = json.loads(committed(execution_commit, DENYSET_PATH))
    if implementation["constructor_implementation_identity"] != "68101cd87711761c2c739dc989490c5dd05eaccc0fac03472b9aac180ce647e4":
        raise SystemExit("implementation identity")
    if implementation["module_sha256"] != CONSTRUCTOR_SHA:
        raise SystemExit("implementation source binding")
    if denyset["fragment_denyset_identity"] != "d35beab3b093d118e52369239477f6dc835e764976e44336793f90704b38c844":
        raise SystemExit("denyset identity")
    release_bytes = committed(RELEASE_COMMIT, RELEASE_PATH)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    if prepared.release_identity != "51c58df40ad779ed8b1e14207b69609980a08bc40f2db6de0b4d8398a9fe1b52":
        raise SystemExit("release identity")
    if prepared.packet_identity != "4e812e402c2d56f5b95f5aa60bd09630117de72377d2a6bb8da0e446ac2634ae":
        raise SystemExit("packet identity")
    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    # Sole authorized constructor invocation. No code below may call it again.
    result = construct_development_candidate_v4(constructor_packet_bytes=packet_bytes)
    packet = json.loads(packet_bytes)
    candidate_bytes = result.candidate_surface_utf8 or b""
    if result.terminal_classification == "CANDIDATE_PRODUCED" and result.candidate_surface_utf8 is not None:
        candidate_bytes.decode("utf-8")
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
        candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT08_CANDIDATE_V1", {
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
        creative_marker_family = seal("B2_CREATIVE_MARKER_FAMILY_V4", {
            "candidate_identity": candidate_id,
            "construction_revision_family_id": packet["construction_revision_family_id"],
        })
        CANDIDATE.write_bytes(candidate_bytes)
    else:
        terminal, candidate_sha, candidate_id = result.terminal_classification, None, None
        creative_family = creative_marker_family = "UNASSIGNED"
    forbidden = (b"HMCV1-", b"ABSURD_LOGICAL_EXTENSION", b"mechanism_id", b"mechanism_name", b"answer_key")
    hidden = any(token.lower() in candidate_bytes.lower() for token in forbidden)
    core = {
        "schema_name": "batch2-development-pilot08-construction-attempt01-v1",
        "schema_version": "1.0.0",
        "execution_source_commit": execution_commit,
        "constructor_access_source_sha256": ACCESS_SHA,
        "constructor_source_sha256": CONSTRUCTOR_SHA,
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "release_commit": RELEASE_COMMIT,
        "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "selected_proposition_id": packet["selected_proposition_id"],
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "construction_revision_family_id": packet["construction_revision_family_id"],
        "attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1},
        "terminal_classification": terminal,
        "failure_code": result.failure_code,
        "candidate_identity": candidate_id,
        "candidate_surface_sha256": candidate_sha,
        "candidate_surface_byte_length": len(candidate_bytes) if candidate_bytes else None,
        "candidate_surface_present": result.candidate_surface_utf8 is not None,
        "candidate_partition": "DEVELOPMENT" if candidate_id else None,
        "creative_premise_family_id": creative_family,
        "creative_marker_family_id": creative_marker_family,
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
            "environment_or_cli_access": False,
            "logs_cache_temp_or_process_access": False,
            "network_or_model_access": False,
            "hidden_mechanism_metadata_introduced": hidden,
        },
        "post_construction_g02b_verdict": "PASS" if not hidden else "FAIL_HIDDEN_METADATA",
        "fragment_collision_evaluation": "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02",
        "g02_eligibility": False,
        "retry_authority": False,
        "repair_authority": False,
        "selection_authority": False,
        "authority_matrix": {key: False for key in ("fragment_collision_evaluation", "g02", "g02c", "g03", "owner_freeze", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT08_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"terminal_classification": terminal, "candidate_identity": candidate_id,
                      "candidate_surface_sha256": candidate_sha, "creative_premise_family_id": creative_family,
                      "creative_marker_family_id": creative_marker_family, "capability_consumed": True,
                      "post_construction_g02b_verdict": evidence["post_construction_g02b_verdict"],
                      "fragment_collision_evaluation": evidence["fragment_collision_evaluation"],
                      "evidence_identity": evidence["evidence_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
