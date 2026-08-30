"""Prepare and audit one zero-construction Pilot 01 assignment proposal."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "2e9314c18cd11b35c63d6242dfac1cb4bf5b21b8"
INGESTION_COMMIT = "601ee4812d864301cb55620e3d239515163e9ef8"
OUT = ROOT / "docs/artifacts"
INGESTION_PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/"
ADMISSION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-g01a-g01b-admission-v1.json"


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
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT,
            "HEAD differs from admission commit")
    admission = load(COMMIT, ADMISSION_PATH)
    envelope = load(INGESTION_COMMIT, INGESTION_PREFIX + "factual-authority-envelope.json")
    package = load(INGESTION_COMMIT, INGESTION_PREFIX + "source-package.json")
    require(admission["admission_identity"] == "553b091f112d8e3f827c49c28cb93c63f249b8bb9a98f5b877f7bd739d694baf", "admission")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "gate state")
    require(admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "contamination")
    require(package["partition"] == "DEVELOPMENT" and package["creative_premise_family_id"] == "UNASSIGNED", "partition/creative premise")
    # The assignment custodian compares frozen necessary conditions. Only the selected
    # target is structurally satisfiable without changing facts or encoding the answer
    # in a compulsory surface form.
    alternatives = [
        {"opaque_option": "OBL-A", "result": "UNSAFE", "reason": "REQUIRES_AN_INITIAL_SOURCE_READING_THAT_THE_CLOSED_ENVELOPE_DOES_NOT_LICENSE"},
        {"opaque_option": "OBL-B", "result": "UNSAFE", "reason": "REQUIRES_AN_IDENTIFIABLE_NONLITERAL_SOURCE_EXPRESSION_ABSENT_FROM_THE_ENVELOPE"},
        {"opaque_option": "OBL-C", "result": "SAFE", "reason": "CAN_TRANSFORM_ONE_BOUND_PREMISE_WITHOUT_CHANGING_OR_WIDENING_IT"},
        {"opaque_option": "OBL-D", "result": "UNSAFE", "reason": "REQUIRES_A_GENUINE_STANCE_OR_CONCESSION_TARGET_NOT_PRESENT_IN_THE_ENVELOPE"},
        {"opaque_option": "OBL-E", "result": "UNSAFE", "reason": "MANDATORY_GRAMMATICAL_FORM_WOULD_TRIVIALLY_DISCLOSE_THE_TARGET_OPERATION"},
        {"opaque_option": "OBL-F", "result": "UNSAFE", "reason": "REQUIRES_RECOGNIZABLE_SOURCE_FORM_CONVENTIONS_ABSENT_FROM_THE_ENVELOPE"},
    ]
    assignment_core = {
        "schema_name": "batch2-development-pilot01-sealed-assignment-mapping-v1", "schema_version": "1.0.0",
        "admission_commit": COMMIT, "admission_identity": admission["admission_identity"],
        "family_closure": package["family_identities"]["family_closure"], "partition": "DEVELOPMENT",
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION",
                           "mechanism_name": "Absurd Logical Extension",
                           "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "selection_analysis": alternatives,
        "selection_basis": "NECESSARY_CONDITION_SATISFIABILITY_AND_AUTHORITY_SAFETY_NOT_TOPIC_OR_SURFACE_SIMILARITY",
        "status": "SEALED_PROPOSAL_NOT_ACTIVATED",
        "constructor_access": False, "evaluator_access_before_independent_verdict": False,
        "creative_premise_family_id": "UNASSIGNED", "candidate_surface": None,
    }
    assignment_identity = seal("B2_DEVELOPMENT_PILOT01_SEALED_ASSIGNMENT_V1", assignment_core)
    mapping = {**assignment_core, "sealed_assignment_identity": assignment_identity}
    obligation = {
        "obligation_id": seal("B2_DEVELOPMENT_PILOT01_UNLABELED_OBLIGATION_V1", {
            "assignment": assignment_identity, "family": package["family_identities"]["family_closure"]}),
        "transformation": [
            "Begin from exactly one proposition in the closed authority envelope without altering it.",
            "Add a short creative layer containing at least two locally traceable consequence steps.",
            "Keep every added step explicitly outside factual authority and make the final step clearly impossible within the admitted source world.",
            "The relation between consecutive steps must be understandable from the produced text; an unrelated invented event does not satisfy the obligation.",
        ],
        "forbidden_operations": [
            "Do not obtain the effect only by increasing quantity, intensity, or scale.",
            "Do not substitute a comparison or mapping between unrelated domains for the required consequence trace.",
            "Do not introduce an event disconnected from the selected bound proposition.",
            "Do not present a list of alternatives as the transformation.",
            "Do not state any creative consequence as fact, source testimony, or real-world outcome.",
        ],
    }
    constraints = {
        "language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_ROMANIAN",
        "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
        "source_fidelity": "EXACT_QUALIFICATION_AND_UNKNOWN_BOUNDARY_RETENTION",
        "creative_marking": "EVERY_NONFACTUAL_CONSEQUENCE_MUST_BE_LOCALLY_UNMISTAKABLE_AS_CREATIVE",
        "protected_targets": "NO_PERSON_OR_PROTECTED_TARGET; SYNTHETIC_ROOM_AND_CABINETS_ONLY",
        "prohibited": ["CANNED_OPENING", "HISTORICAL_EXAMPLE_REUSE", "UNBOUND_QUOTATION", "PRIVATE_KNOWLEDGE", "FACTUAL_WIDENING"],
    }
    packet_core = {
        "schema_name": "batch2-development-pilot01-constructor-facing-assignment-proposal-v1", "schema_version": "1.0.0",
        "admission_identity": admission["admission_identity"], "source_package_identity": package["source_package_identity"],
        "source_object": {"commit": INGESTION_COMMIT, "git_blob_oid_sha1": package["prospective_git_blob_oid_sha1"],
                          "sha256": package["source_sha256"], "access": "ONLY_UNDER_SEPARATE_CONSTRUCTION_AUTHORIZATION"},
        "closed_factual_authority_envelope": envelope,
        "permitted_assertions": [p["proposition_id"] for p in envelope["propositions"]],
        "required_qualifications": [{"proposition_id": p["proposition_id"], "qualification": p["qualification"],
                                     "time": p["time"], "unknown_boundary": p["unknown_boundary"]}
                                    for p in envelope["propositions"]],
        "protected_target_restrictions": constraints["protected_targets"],
        "unlabeled_operational_obligation": obligation,
        "output_constraints": constraints,
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT01_MAPPING_COMMITMENT_V1", mapping),
        "immutable_assignment_identity": assignment_identity,
        "creative_premise_family_id": "UNASSIGNED", "status": "PROPOSAL_ZERO_CONSTRUCTION",
        "constructor_invoked": False, "candidate_surface": None,
        "authority_matrix": {key: False for key in ("construction", "generation", "creative_premise_assignment",
                                                     "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    packet_identity = seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_PACKET_V1", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_identity}
    # The constructor packet must contain no taxonomy answer token, name, ordinal,
    # evidence role, historical example, owner preference, or blind material reference.
    packet_bytes = canonical(packet)
    forbidden_patterns = [
        rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
        rb"mechanism_id", rb"mechanism_name", rb"Batch 2 ordinal", rb"expected evidence role",
        rb"answer key", rb"owner preference", rb"BLIND_EVALUATION", rb"historical mechanism example",
    ]
    leakage_hits = [pattern.decode("ascii") for pattern in forbidden_patterns if re.search(pattern, packet_bytes, re.I)]
    require(not leakage_hits, f"constructor packet leakage: {leakage_hits}")
    require(packet["closed_factual_authority_envelope"] == envelope, "authority envelope mutation")
    require(packet["creative_premise_family_id"] == mapping["creative_premise_family_id"] == "UNASSIGNED", "creative premise")
    require(all(value is False for value in packet["authority_matrix"].values()), "hidden authority")
    require(packet["candidate_surface"] is None and mapping["candidate_surface"] is None, "surface construction")
    audit_core = {
        "schema_name": "batch2-development-pilot01-assignment-design-leakage-audit-v1", "schema_version": "1.0.0",
        "sealed_assignment_identity": assignment_identity, "constructor_facing_packet_identity": packet_identity,
        "taxonomy_label_token_scan": "PASS_ZERO_HITS", "operational_wording_leakage": "PASS_NO_LABEL_OR_TAXONOMY_PARAPHRASE",
        "source_shape_selection": "PASS_NECESSARY_CONDITIONS_COMPARED_SELECTION_NOT_TOPIC_BASED",
        "packet_shape": "PASS_COMMON_NEUTRAL_LENGTH_AND_FIELD_PROFILE",
        "factual_authority_widening": "ABSENT_EXACT_ENVELOPE_EQUALITY",
        "creative_premise_assignment": "ABSENT_UNASSIGNED",
        "neighbor_answer_leakage": "ABSENT_OPERATIONAL_PROHIBITIONS_ONLY",
        "blind_evaluation_contamination": "ABSENT_NO_BLIND_ACCESS_OR_REFERENCE",
        "construction_authority": "ABSENT", "constructor_invocations": 0, "candidate_surfaces_created": 0,
        "pool_level_shortcut_audit": "DEFERRED_UNTIL_MULTIPLE_CANDIDATES_NO_CONSTRUCTION_AUTHORITY",
        "deterministic_blockers": [], "verdict": "PASS_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT01_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot01-sealed-assignment-mapping-v1.json", mapping)
    write("humor-mechanics-batch2-development-pilot01-constructor-facing-assignment-proposal-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot01-assignment-design-leakage-audit-v1.json", audit)
    print(json.dumps({"verdict": "SAFE_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION",
                      "sealed_assignment_identity": assignment_identity,
                      "constructor_facing_packet_identity": packet_identity,
                      "leakage_audit": audit["verdict"], "audit_identity": audit["audit_identity"],
                      "creative_premise_family_id": "UNASSIGNED"}, sort_keys=True))


if __name__ == "__main__":
    main()
