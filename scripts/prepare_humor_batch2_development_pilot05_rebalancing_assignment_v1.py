"""Prepare Pilot 05's label-blind post-G01 rebalancing assignment proposal."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
ADMISSION_COMMIT = "eb920f7b4bcf5473d22733c22520087fdf20a571"
INGESTION_COMMIT = "585c986e0bd6b4717b3a1e90aad4aa5a7c8c0373"
GOVERNANCE_COMMIT = "618333a3db484da134904aea004a36e9cb0350d4"
G04B_COMMIT = "9a5eddc8442a9119e22049b2221e34e56556588f"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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
    path = ART / name
    require(not path.exists(), f"already exists: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == ADMISSION_COMMIT,
            "HEAD differs from Pilot 05 admission commit")
    admission = load(ADMISSION_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot05-g01a-g01b-admission-v1.json")
    prefix = "docs/artifacts/humor-mechanics-batch2-development-pilot05-ingestion-v1/"
    envelope = load(INGESTION_COMMIT, prefix + "factual-authority-envelope.json")
    package = load(INGESTION_COMMIT, prefix + "source-package.json")
    source = raw(INGESTION_COMMIT, prefix + "source.utf8.txt")
    governance = load(GOVERNANCE_COMMIT, "docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v2.json")
    pool_audit = load(G04B_COMMIT, "docs/artifacts/humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-v1.json")
    require(admission["admission_identity"] == "ff0d4ef7c263e30b6b944bde6d91b7d41e321678dd9fa7dc3bfc011312eafaee", "admission")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01 gates")
    require(admission["post_g01_rebalancing_assignment_gate"] == "NOT_PERFORMED_SEPARATELY_AUTHORIZED_ONLY", "gate state")
    require(admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "contamination")
    require(package["partition"] == "DEVELOPMENT" and package["creative_premise_family_id"] == "UNASSIGNED", "partition")
    require(pool_audit["g04b_pool_audit_identity"] == "75b7644656e1e111f38998de07034aacca74c6eee0eccd813acbb201c0a433b7", "G04B")
    require(pool_audit["g04b_verdict"] == "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION", "G04B state")
    governance_core = dict(governance)
    governance_id = governance_core.pop("obligation_governance_identity")
    require(governance_id == "874c5d611c5ab955e0f9d82aa5aa086fad98e065f66e20e9e236f48798287024", "governance")
    require(seal("B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V2", governance_core) == governance_id, "governance seal")

    formulation_core = {
        "schema_name": "batch2-development-pilot05-rebalancing-obligation-family-v1",
        "schema_version": "1.0.0",
        "family_version": "REVERSE_DISCLOSURE_DEPENDENCY_V1",
        "bound_base_governance_identity": governance_id,
        "constructor_visible_obligation": {
            "obligation_version": "REVERSE_DISCLOSURE_DEPENDENCY_V1",
            "transformation": [
                "Păstrează fără schimbare de conținut sau calificare exact o propoziție autorizată, integrată firesc în text.",
                "Prezintă mai întâi un rezultat concret și neechivoc inventat, apoi fă inteligibilă legătura lui cu relația factuală prin două trepte de dependență recuperabile în sens invers.",
                "Fiecare treaptă trebuie să depindă de cea imediat următoare în explicație și să nu poată fi înlocuită cu o întâmplare arbitrară.",
                "Rezultatul inventat și cele două trepte trebuie să rămână clar în afara autorității factuale, prin construcția idiomatică a enunțului.",
            ],
            "forbidden_operations": [
                "Nu face ca poanta să depindă de atribuirea unei alte denumiri, categorii, definiții sau stări unei entități.",
                "Nu atribui entităților nonumane vorbire, intenție, emoție, ocupație, rol social ori agenție umană neautorizată.",
                "Nu obține rezultatul numai prin comparație, intensificare, listă, joc lexical sau surpriză fără dependența completă.",
                "Nu folosi un eveniment inventat fără legătură cu propoziția factuală aleasă.",
            ],
            "naturalness_and_surface_freedom": [
                "Folosește română idiomatică și concretă; nu transfera în suprafață limbaj de guvernanță, verificare sau instrucțiune.",
                "Nu este impus niciun conector, semn de punctuație, cuvânt de aterizare, registru, număr de propoziții sau formulă de poantă.",
                "Nu folosi o prefață de tipul «în poveste» și nu începe cu relatarea factuală urmată de un lanț expus numai înainte.",
            ],
            "factual_safety": governance["constructor_visible_obligation"]["factual_safety"],
        },
        "structural_difference_from_pilot03_pilot04": {
            "prior_family": governance["constructor_visible_obligation"]["obligation_version"],
            "prior_order": "FACT_THEN_FORWARD_TWO_SITUATION_CHAIN",
            "successor_order": "FICTIONAL_CONSEQUENCE_THEN_REVERSE_DISCLOSED_TWO_LINK_DEPENDENCY",
            "story_preface_prohibited": True,
            "semicolon_required": False,
            "ajunge_or_other_landing_lexeme_required": False,
            "reclassification_payoff_prohibited": True,
        },
        "source_selection_influence": False,
        "candidate_surface": None,
        "construction_authority": False,
    }
    formulation_id = seal("B2_DEVELOPMENT_PILOT05_REBALANCING_OBLIGATION_FAMILY_V1", formulation_core)
    formulation = {**formulation_core, "obligation_family_identity": formulation_id}
    require(formulation_id != seal("B2_DEVELOPMENT_PILOT05_REBALANCING_OBLIGATION_FAMILY_V1", {**formulation_core, "family_version": governance["constructor_visible_obligation"]["obligation_version"]}), "family distinction")

    satisfiability = {p["proposition_id"]: {
        "closed_authority_available": True,
        "qualification_and_unknown_boundary_bound": True,
        "reverse_disclosure_dependency_not_precluded": True,
        "reclassification_or_human_agency_required": False,
    } for p in envelope["propositions"]}
    require(len(satisfiability) == 7 and all(not item["reclassification_or_human_agency_required"] for item in satisfiability.values()), "satisfiability")
    assignment_core = {
        "schema_name": "batch2-development-pilot05-sealed-rebalancing-assignment-mapping-v1",
        "schema_version": "1.0.0",
        "admission_commit": ADMISSION_COMMIT,
        "admission_identity": admission["admission_identity"],
        "family_closure": package["family_identities"]["family_closure"],
        "partition": "DEVELOPMENT",
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "mechanism_name": "Absurd Logical Extension", "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "close_alternative_profile": {
            "primary_neighbor": "MISDIRECTION",
            "secondary_neighbors": ["ESCALATION", "HYPERBOLE"],
            "required_closed_choices": ["TARGET", "MISDIRECTION", "ESCALATION", "HYPERBOLE", "NONE", "AMBIGUOUS"],
            "comic_reclassification_excluded_as_designed_support": True,
            "difference_from_pilot03_pilot04": "PASS_DISTINCT_PRIMARY_NEIGHBOR_AND_NO_RECLASSIFICATION_PAYOFF",
        },
        "obligation_family_identity": formulation_id,
        "selection_analysis": {
            "source_acquired_and_g01_admitted_before_assignment": True,
            "source_selected_or_shaped_using_target_obligation_or_pool_need": False,
            "all_seven_propositions_structurally_satisfiable": satisfiability,
            "basis": "POST_G01_GOVERNANCE_SATISFIABILITY_AND_POOL_REBALANCING_ONLY",
        },
        "status": "SEALED_REBALANCING_PROPOSAL_NOT_ACTIVATED",
        "constructor_access": False,
        "evaluator_access_before_blind_verdict": False,
        "creative_premise_family_id": "UNASSIGNED",
        "candidate_surface": None,
    }
    assignment_id = seal("B2_DEVELOPMENT_PILOT05_SEALED_REBALANCING_ASSIGNMENT_V1", assignment_core)
    mapping = {**assignment_core, "sealed_assignment_identity": assignment_id}
    obligation_instance = seal("B2_DEVELOPMENT_PILOT05_UNLABELED_REBALANCING_OBLIGATION_INSTANCE_V1", {"assignment": assignment_id, "family": package["family_identities"]["family_closure"], "obligation_family_identity": formulation_id})
    packet_core = {
        "schema_name": "batch2-development-pilot05-constructor-facing-assignment-proposal-v1",
        "schema_version": "1.0.0",
        "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "source_object": {"commit": INGESTION_COMMIT, "git_blob_oid_sha1": package["prospective_git_blob_oid_sha1"], "sha256": package["source_sha256"], "byte_length": len(source)},
        "exact_source_utf8": source.decode("utf-8"),
        "closed_factual_authority_envelope": envelope,
        "permitted_assertions": [p["proposition_id"] for p in envelope["propositions"]],
        "required_qualifications": [{"proposition_id": p["proposition_id"], "qualification": p["qualification"], "time": p["time"], "scope": p["scope"], "unknown_boundary": p["unknown_boundary"]} for p in envelope["propositions"]],
        "protected_target_restrictions": "NO_REAL_PERSON_OR_PROTECTED_TARGET; OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "unlabeled_operational_obligation": {"obligation_instance_identity": obligation_instance, **formulation["constructor_visible_obligation"]},
        "output_constraints": {"language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_CONCRETE_ROMANIAN", "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES", "source_fidelity": "EXACT_QUALIFICATION_TIME_SCOPE_AND_UNKNOWN_BOUNDARY_RETENTION", "prohibited": ["CANNED_OPENING", "GOVERNANCE_OR_EDITORIAL_META_LANGUAGE", "PROCEDURAL_ABSTRACT_REGISTER", "HISTORICAL_EXAMPLE_REUSE", "UNBOUND_QUOTATION", "PRIVATE_KNOWLEDGE", "FACTUAL_WIDENING"]},
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT05_REBALANCING_MAPPING_COMMITMENT_V1", mapping),
        "immutable_assignment_identity": assignment_id,
        "creative_premise_family_id": "UNASSIGNED",
        "status": "PROPOSAL_ZERO_CONSTRUCTION",
        "constructor_invoked": False,
        "candidate_surface": None,
        "authority_matrix": {key: False for key in ("construction", "generation", "creative_premise_assignment", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    packet_id = seal("B2_DEVELOPMENT_PILOT05_REBALANCING_CONSTRUCTOR_PACKET_V1", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"MISDIRECTION", rb"ESCALATION", rb"HYPERBOLE", rb"reclasific", rb"rebalanc", rb"g04b", rb"pool", rb"candida.t.*anterior", rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"answer key", rb"owner preference", rb"BLIND_EVALUATION"]
    hits = [pattern.decode("ascii") for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"constructor-visible leakage: {hits}")
    require(packet["exact_source_utf8"].encode("utf-8") == source and packet["closed_factual_authority_envelope"] == envelope, "source/envelope")
    require(packet["creative_premise_family_id"] == mapping["creative_premise_family_id"] == "UNASSIGNED", "creative premise")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot05-rebalancing-assignment-design-audit-v1",
        "schema_version": "1.0.0",
        "sealed_assignment_identity": assignment_id,
        "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": formulation_id,
        "distinct_from_pilot03_pilot04_obligation_family": "PASS_REVERSE_DISCLOSURE_VS_FORWARD_CHAIN",
        "distinct_close_alternative_profile": "PASS_MISDIRECTION_PRIMARY_NO_COMIC_RECLASSIFICATION_SUPPORT_DESIGN",
        "taxonomy_and_alternative_label_scan": "PASS_ZERO_HITS",
        "source_shape_selection": "PASS_SOURCE_ACQUIRED_AND_G01_ADMITTED_BEFORE_REBALANCING_GATE",
        "factual_authority_widening": "ABSENT_EXACT_ENVELOPE_EQUALITY",
        "creative_premise_assignment": "ABSENT_UNASSIGNED",
        "blind_evaluation_contamination": "ABSENT",
        "construction_authority": "ABSENT",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "g04b_certification_performed": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT05_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot05-rebalancing-obligation-family-v1.json", formulation)
    write("humor-mechanics-batch2-development-pilot05-sealed-rebalancing-assignment-v1.json", mapping)
    write("humor-mechanics-batch2-development-pilot05-constructor-facing-rebalancing-assignment-proposal-v1.json", packet)
    write("humor-mechanics-batch2-development-pilot05-rebalancing-assignment-design-audit-v1.json", audit)
    print(json.dumps({"verdict": "SAFE_REBALANCING_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION", "obligation_family_identity": formulation_id, "sealed_assignment_identity": assignment_id, "constructor_facing_packet_identity": packet_id, "obligation_instance_identity": obligation_instance, "audit_identity": audit["audit_identity"], "creative_premise_family_id": "UNASSIGNED"}, sort_keys=True))


if __name__ == "__main__":
    main()
