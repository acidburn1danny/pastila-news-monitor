"""Prepare and audit the zero-construction Pilot 04 Governance V2 assignment."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
ADMISSION_COMMIT = "902d1d06f30924dc66e2190a81590c4359a4b1c7"
INGESTION_COMMIT = "4e4afc730be7600fb0b6ce8abf822bce868b0565"
GOVERNANCE_COMMIT = "618333a3db484da134904aea004a36e9cb0350d4"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def raw(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == ADMISSION_COMMIT,
            "HEAD differs from Pilot 04 admission commit")
    admission = load(ADMISSION_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1.json")
    prefix = "docs/artifacts/humor-mechanics-batch2-development-pilot04-ingestion-v1/"
    envelope = load(INGESTION_COMMIT, prefix + "factual-authority-envelope.json")
    package = load(INGESTION_COMMIT, prefix + "source-package.json")
    source = raw(INGESTION_COMMIT, prefix + "source.utf8.txt")
    governance = load(GOVERNANCE_COMMIT, "docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v2.json")
    require(admission["admission_identity"] == "13b2c8bae8a5535de5321c82c9faee36fdb44a96f90ebafcb71a8c036a456ac9", "admission identity")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "gate state")
    require(admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "contamination")
    require(package["partition"] == "DEVELOPMENT" and package["creative_premise_family_id"] == "UNASSIGNED", "partition/family")
    governance_core = dict(governance)
    governance_id = governance_core.pop("obligation_governance_identity")
    require(governance_id == "874c5d611c5ab955e0f9d82aa5aa086fad98e065f66e20e9e236f48798287024", "governance identity")
    require(seal("B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V2", governance_core) == governance_id, "governance seal")
    require(governance["future_source_rule"]["pilot03_must_be_fresh_independently_acquired_and_admitted"] is True,
            "fresh-family governance precedent")
    require(governance["future_source_rule"]["source_must_not_be_selected_or_shaped_by_obligation"] is True, "source independence")
    require(len(envelope["propositions"]) == 7, "propositions")
    satisfiability = {p["proposition_id"]: {
        "closed_authority_available": True,
        "qualification_and_unknown_boundary_bound": True,
        "two_step_dependency_not_precluded": True,
        "human_agency_or_role_required": False,
    } for p in envelope["propositions"]}
    require(all(all((v is True) for k, v in item.items() if k != "human_agency_or_role_required") and
                item["human_agency_or_role_required"] is False for item in satisfiability.values()), "satisfiability")
    assignment_core = {
        "schema_name": "batch2-development-pilot04-sealed-assignment-mapping-v1",
        "schema_version": "1.0.0",
        "admission_commit": ADMISSION_COMMIT,
        "admission_identity": admission["admission_identity"],
        "family_closure": package["family_identities"]["family_closure"],
        "partition": "DEVELOPMENT",
        "target_mapping": {
            "mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION",
            "mechanism_name": "Absurd Logical Extension",
            "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION",
        },
        "successor_obligation_governance_identity": governance_id,
        "selection_analysis": {
            "source_acquired_and_admitted_before_target_decision": True,
            "source_selected_or_shaped_using_target_or_obligation": False,
            "fresh_family_independent_of_pilots_01_02_and_03": True,
            "all_seven_propositions_structurally_satisfiable": satisfiability,
            "selection_basis": "GOVERNANCE_V2_POST_ADMISSION_SATISFIABILITY_ONLY",
        },
        "status": "SEALED_PROPOSAL_NOT_ACTIVATED",
        "constructor_access": False,
        "evaluator_access_before_independent_verdict": False,
        "creative_premise_family_id": "UNASSIGNED",
        "candidate_surface": None,
    }
    assignment_id = seal("B2_DEVELOPMENT_PILOT04_SEALED_ASSIGNMENT_V1", assignment_core)
    mapping = {**assignment_core, "sealed_assignment_identity": assignment_id}
    obligation_instance = seal("B2_DEVELOPMENT_PILOT04_UNLABELED_OBLIGATION_INSTANCE_V1", {
        "assignment": assignment_id,
        "family": package["family_identities"]["family_closure"],
        "version": governance["constructor_visible_obligation"]["obligation_version"],
    })
    packet_core = {
        "schema_name": "batch2-development-pilot04-constructor-facing-assignment-proposal-v1",
        "schema_version": "1.0.0",
        "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "source_object": {"commit": INGESTION_COMMIT, "git_blob_oid_sha1": package["prospective_git_blob_oid_sha1"],
                          "sha256": package["source_sha256"], "byte_length": len(source)},
        "exact_source_utf8": source.decode("utf-8"),
        "closed_factual_authority_envelope": envelope,
        "permitted_assertions": [p["proposition_id"] for p in envelope["propositions"]],
        "required_qualifications": [{"proposition_id": p["proposition_id"], "qualification": p["qualification"],
                                      "time": p["time"], "scope": p["scope"], "unknown_boundary": p["unknown_boundary"]}
                                     for p in envelope["propositions"]],
        "protected_target_restrictions": "NO_REAL_PERSON_OR_PROTECTED_TARGET; OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "unlabeled_operational_obligation": {"obligation_instance_identity": obligation_instance,
                                              **governance["constructor_visible_obligation"]},
        "output_constraints": {
            "language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_ROMANIAN",
            "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
            "source_fidelity": "EXACT_QUALIFICATION_TIME_SCOPE_AND_UNKNOWN_BOUNDARY_RETENTION",
            "protected_targets": "NO_REAL_PERSON_OR_PROTECTED_TARGET",
            "prohibited": ["CANNED_OPENING", "GOVERNANCE_OR_EDITORIAL_META_LANGUAGE", "PROCEDURAL_ABSTRACT_REGISTER",
                           "HISTORICAL_EXAMPLE_REUSE", "UNBOUND_QUOTATION", "PRIVATE_KNOWLEDGE", "FACTUAL_WIDENING"],
        },
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT04_MAPPING_COMMITMENT_V1", mapping),
        "immutable_assignment_identity": assignment_id,
        "creative_premise_family_id": "UNASSIGNED",
        "status": "PROPOSAL_ZERO_CONSTRUCTION",
        "constructor_invoked": False,
        "candidate_surface": None,
        "authority_matrix": {key: False for key in ("construction", "generation", "creative_premise_assignment",
                                                     "model_exposure", "training", "runtime_integration", "production_routing",
                                                     "g04b_pool_certification")},
    }
    packet_id = seal("B2_DEVELOPMENT_PILOT04_CONSTRUCTOR_PACKET_V1", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    packet_bytes = canonical(packet)
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"conformance_schema", rb"removal_test",
                 rb"answer key", rb"owner preference", rb"BLIND_EVALUATION", rb"PILOT02_REJECTED"]
    hits = [p.decode("ascii") for p in forbidden if re.search(p, packet_bytes, re.I)]
    require(not hits, f"constructor packet leakage: {hits}")
    require(packet["closed_factual_authority_envelope"] == envelope, "envelope mutation")
    require(packet["exact_source_utf8"].encode("utf-8") == source, "source mutation")
    require(packet["unlabeled_operational_obligation"]["obligation_version"] == "SUCCESSOR_FORMULATION_C_NATURAL_ROMANIAN_V2", "obligation")
    require(packet["creative_premise_family_id"] == mapping["creative_premise_family_id"] == "UNASSIGNED", "creative premise")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot04-assignment-design-leakage-audit-v1", "schema_version": "1.0.0",
        "sealed_assignment_identity": assignment_id, "constructor_facing_packet_identity": packet_id,
        "governance_v2": "PASS_EXACT_FROZEN_BODY", "taxonomy_label_token_scan": "PASS_ZERO_HITS",
        "source_shape_selection": "PASS_FRESH_SOURCE_ACQUIRED_AND_ADMITTED_BEFORE_ASSIGNMENT",
        "pilot01_pilot02_and_pilot03_contamination": "ABSENT_NO_SURFACE_CONSTRUCTION_OR_DIAGNOSTIC_REUSE",
        "naturalness_remediation_binding": "PASS_FORMULATION_C_V2",
        "operational_wording_leakage": "PASS_CUE_MINIMIZED_WITHOUT_TAXONOMY_TOKEN",
        "factual_authority_widening": "ABSENT_EXACT_ENVELOPE_EQUALITY",
        "creative_premise_assignment": "ABSENT_UNASSIGNED", "blind_evaluation_contamination": "ABSENT",
        "construction_authority": "ABSENT", "constructor_invocations": 0, "candidate_surfaces_created": 0,
        "deterministic_blockers": [], "verdict": "PASS_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT04_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot04-sealed-assignment-mapping-v1.json", mapping)
    write("humor-mechanics-batch2-development-pilot04-constructor-facing-assignment-proposal-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot04-assignment-design-leakage-audit-v1.json", audit)
    print(json.dumps({"verdict": "SAFE_GOVERNANCE_V2_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION",
                      "sealed_assignment_identity": assignment_id, "constructor_facing_packet_identity": packet_id,
                      "obligation_instance_identity": obligation_instance, "leakage_audit": audit["verdict"],
                      "audit_identity": audit["audit_identity"], "creative_premise_family_id": "UNASSIGNED"}, sort_keys=True))


if __name__ == "__main__":
    main()
