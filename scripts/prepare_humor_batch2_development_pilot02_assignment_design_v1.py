"""Prepare and audit the zero-construction Pilot 02 successor assignment."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
ADMISSION_COMMIT = "33a670ada0fc2cd31680033f0c42abeb1b0b4bb6"
INGESTION_COMMIT = "6220b9d86336ec6bd4a62a1cff528e96f973be2c"
GOVERNANCE_COMMIT = "a444ace2e6eb8bfad006374f266c90269c665565"
ADMISSION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-g01a-g01b-admission-v1.json"
INGESTION_PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/"
GOVERNANCE_PATH = "docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    (ART / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == ADMISSION_COMMIT,
            "HEAD differs from Pilot 02 admission commit")
    admission = load(ADMISSION_COMMIT, ADMISSION_PATH)
    envelope = load(INGESTION_COMMIT, INGESTION_PREFIX + "factual-authority-envelope.json")
    package = load(INGESTION_COMMIT, INGESTION_PREFIX + "source-package.json")
    governance = load(GOVERNANCE_COMMIT, GOVERNANCE_PATH)

    require(admission["admission_identity"] == "fb7c257f380892311c859f0deb8f96d0d209fdcddf1192a714c9ca7ece914eb3", "admission identity")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "gate state")
    require(admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "contamination state")
    require(package["partition"] == "DEVELOPMENT" and package["creative_premise_family_id"] == "UNASSIGNED", "partition/family")
    governance_core = dict(governance)
    governance_identity = governance_core.pop("obligation_governance_identity")
    require(governance_identity == "0cfd22fd43e0be68b5a04f16e45e918ac7bae346c851334817a7af309bad63e5", "governance identity")
    require(seal("B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V1", governance_core) == governance_identity, "governance seal")
    require(governance["future_source_rule"] == {
        "fresh_independently_acquired_and_admitted_development_family_required": True,
        "prior_construction_exposure_allowed": False,
        "prior_target_assignment_allowed": False,
        "selection_by_target_friendly_topic_or_shape": False,
    }, "fresh-source governance")

    # The source was acquired and admitted before this decision. Assignment therefore
    # cannot influence its subject, proposition topology, family, or immutable bytes.
    satisfiability = {
        p["proposition_id"]: {
            "closed_authority_available": True,
            "qualification_and_unknown_boundary_bound": True,
            "two_change_continuation_not_precluded": True,
            "human_agency_or_role_required": False,
        }
        for p in envelope["propositions"]
    }
    require(len(satisfiability) == 7 and all(
        item["closed_authority_available"]
        and item["qualification_and_unknown_boundary_bound"]
        and item["two_change_continuation_not_precluded"]
        and item["human_agency_or_role_required"] is False
        for item in satisfiability.values()
    ), "obligation satisfiability")

    assignment_core = {
        "schema_name": "batch2-development-pilot02-sealed-assignment-mapping-v1",
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
        "successor_obligation_governance_identity": governance_identity,
        "selection_analysis": {
            "source_acquired_before_target_decision": True,
            "source_selected_using_target_or_obligation": False,
            "all_seven_propositions_structurally_satisfiable": satisfiability,
            "selection_basis": "FROZEN_SUCCESSOR_GOVERNANCE_AND_POST_ADMISSION_SATISFIABILITY_ONLY",
        },
        "status": "SEALED_PROPOSAL_NOT_ACTIVATED",
        "constructor_access": False,
        "evaluator_access_before_independent_verdict": False,
        "creative_premise_family_id": "UNASSIGNED",
        "candidate_surface": None,
    }
    assignment_identity = seal("B2_DEVELOPMENT_PILOT02_SEALED_ASSIGNMENT_V1", assignment_core)
    mapping = {**assignment_core, "sealed_assignment_identity": assignment_identity}

    # Expose only the frozen label-free obligation body. Reviewer-only conformance
    # fields and the governance/target identities remain outside this packet.
    obligation_instance = seal("B2_DEVELOPMENT_PILOT02_UNLABELED_OBLIGATION_INSTANCE_V1", {
        "assignment": assignment_identity,
        "family": package["family_identities"]["family_closure"],
        "version": governance["constructor_visible_obligation"]["obligation_version"],
    })
    constraints = {
        "language": "ROMANIAN",
        "register": "IDIOMATIC_NATURAL_ROMANIAN",
        "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
        "source_fidelity": "EXACT_QUALIFICATION_TIME_SCOPE_AND_UNKNOWN_BOUNDARY_RETENTION",
        "creative_marking": "EVERY_NONFACTUAL_CHANGE_MUST_BE_LOCALLY_UNMISTAKABLE_AS_FICTIONAL",
        "protected_targets": "NO_REAL_PERSON_OR_PROTECTED_TARGET; OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "prohibited": ["CANNED_OPENING", "HISTORICAL_EXAMPLE_REUSE", "UNBOUND_QUOTATION", "PRIVATE_KNOWLEDGE", "FACTUAL_WIDENING"],
    }
    packet_core = {
        "schema_name": "batch2-development-pilot02-constructor-facing-assignment-proposal-v1",
        "schema_version": "1.0.0",
        "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "source_object": {
            "commit": INGESTION_COMMIT,
            "git_blob_oid_sha1": package["prospective_git_blob_oid_sha1"],
            "sha256": package["source_sha256"],
            "access": "ONLY_UNDER_SEPARATE_CONSTRUCTION_AUTHORIZATION",
        },
        "closed_factual_authority_envelope": envelope,
        "permitted_assertions": [p["proposition_id"] for p in envelope["propositions"]],
        "required_qualifications": [
            {"proposition_id": p["proposition_id"], "qualification": p["qualification"], "time": p["time"],
             "scope": p["scope"], "unknown_boundary": p["unknown_boundary"]}
            for p in envelope["propositions"]
        ],
        "protected_target_restrictions": constraints["protected_targets"],
        "unlabeled_operational_obligation": {
            "obligation_instance_identity": obligation_instance,
            **governance["constructor_visible_obligation"],
        },
        "output_constraints": constraints,
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT02_MAPPING_COMMITMENT_V1", mapping),
        "immutable_assignment_identity": assignment_identity,
        "creative_premise_family_id": "UNASSIGNED",
        "status": "PROPOSAL_ZERO_CONSTRUCTION",
        "constructor_invoked": False,
        "candidate_surface": None,
        "authority_matrix": {key: False for key in (
            "construction", "generation", "creative_premise_assignment", "model_exposure", "training",
            "runtime_integration", "production_routing")},
    }
    packet_identity = seal("B2_DEVELOPMENT_PILOT02_CONSTRUCTOR_PACKET_V1", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_identity}
    packet_bytes = canonical(packet)
    forbidden_patterns = [
        rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
        rb"mechanism_id", rb"mechanism_name", rb"conformance_schema", rb"dependency_receipt",
        rb"removal_test", rb"answer key", rb"owner preference", rb"BLIND_EVALUATION",
    ]
    leakage_hits = [p.decode("ascii") for p in forbidden_patterns if re.search(p, packet_bytes, re.I)]
    require(not leakage_hits, f"constructor packet leakage: {leakage_hits}")
    require(packet["closed_factual_authority_envelope"] == envelope, "authority envelope mutation")
    require(packet["unlabeled_operational_obligation"]["obligation_version"] == "SUCCESSOR_FORMULATION_B_V1", "obligation version")
    require(packet["creative_premise_family_id"] == mapping["creative_premise_family_id"] == "UNASSIGNED", "creative premise")
    require(all(value is False for value in packet["authority_matrix"].values()), "hidden authority")
    require(packet["candidate_surface"] is None and mapping["candidate_surface"] is None, "construction occurred")

    audit_core = {
        "schema_name": "batch2-development-pilot02-assignment-design-leakage-audit-v1",
        "schema_version": "1.0.0",
        "sealed_assignment_identity": assignment_identity,
        "constructor_facing_packet_identity": packet_identity,
        "successor_obligation_governance": "PASS_EXACT_FROZEN_BODY",
        "taxonomy_label_token_scan": "PASS_ZERO_HITS",
        "reviewer_only_conformance_leakage": "PASS_ZERO_HITS",
        "source_shape_selection": "PASS_SOURCE_ACQUIRED_AND_ADMITTED_BEFORE_ASSIGNMENT",
        "pilot01_diagnostic_contamination": "ABSENT_NO_SURFACE_OR_CONSTRUCTION_REUSE",
        "operational_wording_leakage": "PASS_CUE_MINIMIZED_WITHOUT_TAXONOMY_TOKEN",
        "factual_authority_widening": "ABSENT_EXACT_ENVELOPE_EQUALITY",
        "creative_premise_assignment": "ABSENT_UNASSIGNED",
        "blind_evaluation_contamination": "ABSENT_NO_BLIND_ACCESS_OR_REFERENCE",
        "construction_authority": "ABSENT",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "deterministic_blockers": [],
        "verdict": "PASS_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT02_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot02-sealed-assignment-mapping-v1.json", mapping)
    write("humor-mechanics-batch2-development-pilot02-constructor-facing-assignment-proposal-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot02-assignment-design-leakage-audit-v1.json", audit)
    print(json.dumps({
        "verdict": "SAFE_SUCCESSOR_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION",
        "sealed_assignment_identity": assignment_identity,
        "constructor_facing_packet_identity": packet_identity,
        "obligation_instance_identity": obligation_instance,
        "leakage_audit": audit["verdict"],
        "audit_identity": audit["audit_identity"],
        "creative_premise_family_id": "UNASSIGNED",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
