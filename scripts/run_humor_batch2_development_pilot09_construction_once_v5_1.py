"""Consume exactly one Pilot 09 V5.1 capability and freeze its observed result."""

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
from pastila_scout.humor_batch2_development_constructor_v5_1 import (
    construct_development_candidate_v5_1,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "2a8f40366a5b215cbf27e6bb55f7ac478682c09f"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-access-release-v5-1.json"
IMPLEMENTATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-1.json"
DENYSET_PATH = "docs/artifacts/humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-1.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot09_construction_once_v5_1.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-construction-attempt01-v1.json"
ACCESS_SHA = "46fc33fd8ecddca23c851840170444a6c59d2ba8476f84fe17aa5b463346625b"
CONSTRUCTOR_SHA = "fffcfde753d46b7ffabb0028a51d3b60b34dee6365b97e0cb3488e372c97566d"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 09 construction attempt already consumed")
    execution_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", RELEASE_COMMIT, execution_commit], cwd=ROOT).returncode:
        raise SystemExit("release commit is not an ancestor")
    runner = (ROOT / RUNNER_PATH).read_bytes()
    if committed(execution_commit, RUNNER_PATH) != runner:
        raise SystemExit("runner is not exact committed execution source")
    access = (ROOT / "src/pastila_scout/humor_batch2_constructor_access_v1.py").read_bytes()
    constructor = (ROOT / "src/pastila_scout/humor_batch2_development_constructor_v5_1.py").read_bytes()
    if hashlib.sha256(access).hexdigest() != ACCESS_SHA or committed(execution_commit, "src/pastila_scout/humor_batch2_constructor_access_v1.py") != access:
        raise SystemExit("access source identity")
    if hashlib.sha256(constructor).hexdigest() != CONSTRUCTOR_SHA or committed(execution_commit, "src/pastila_scout/humor_batch2_development_constructor_v5_1.py") != constructor:
        raise SystemExit("constructor source identity")
    implementation = json.loads(committed(execution_commit, IMPLEMENTATION_PATH))
    denyset = json.loads(committed(execution_commit, DENYSET_PATH))
    if implementation["constructor_implementation_identity"] != "c7134743e6b0e7c3ed7637bff3203f774159f192fef7a7b712e15d4d44a6f419" or implementation["module_sha256"] != CONSTRUCTOR_SHA:
        raise SystemExit("implementation binding")
    if denyset["fragment_denyset_identity"] != "6689d0ae8006dbe9e874ab8e7f537509e2739db4f8a8635510f2152e164a545e":
        raise SystemExit("denyset identity")
    release_bytes = committed(RELEASE_COMMIT, RELEASE_PATH)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    if prepared.release_identity != "32e190fda35752d5bb461e071fcd3eb6ab506e75ab07ce7328c954a6f82bf4a9":
        raise SystemExit("release identity")
    if prepared.packet_identity != "f59803859660dcd29d7934873c80ce9febbf16c422d937ab4c8dd7a214c3446d":
        raise SystemExit("packet identity")
    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    # Sole authorized constructor invocation. No code below may call it again.
    result = construct_development_candidate_v5_1(constructor_packet_bytes=packet_bytes)
    packet = json.loads(packet_bytes)
    candidate_bytes = result.candidate_surface_utf8 or b""
    if result.terminal_classification == "CANDIDATE_PRODUCED" and result.candidate_surface_utf8 is not None:
        candidate_bytes.decode("utf-8")
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
        candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT09_CANDIDATE_V1", {
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
        creative_marker_family = seal("B2_CREATIVE_MARKER_FAMILY_V5_1", {
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
        "schema_name": "batch2-development-pilot09-construction-attempt01-v1",
        "schema_version": "1.0.0",
        "execution_source_commit": execution_commit,
        "constructor_access_source_sha256": ACCESS_SHA,
        "constructor_source_sha256": CONSTRUCTOR_SHA,
        "constructor_contract_identity": packet["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "constructor_source_compatibility_identity": packet["constructor_source_compatibility_identity"],
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "release_commit": RELEASE_COMMIT,
        "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "selected_proposition_id": packet["selected_proposition_id"],
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "typed_plan_commitment": packet["typed_plan_commitment"],
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
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "terminal_classification": terminal,
        "candidate_identity": candidate_id,
        "candidate_surface_sha256": candidate_sha,
        "creative_premise_family_id": creative_family,
        "creative_marker_family_id": creative_marker_family,
        "capability_consumed": True,
        "post_construction_g02b_verdict": evidence["post_construction_g02b_verdict"],
        "fragment_collision_evaluation": evidence["fragment_collision_evaluation"],
        "evidence_identity": evidence["evidence_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
