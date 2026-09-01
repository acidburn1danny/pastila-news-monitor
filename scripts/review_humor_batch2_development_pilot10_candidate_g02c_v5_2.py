"""Mechanism-neutral Governance V5.2 G02C review for Pilot 10 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "542cd2492811ddcac60686a80448c0a4fb5b0d85"
PACKET_COMMIT = "84b4fe215683c9a5fb82e94a8c13ae6c97807179"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-g02b-v5-2.json"
SCHEMA_PATH = "docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(git_bytes(commit, path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def surface_span(text: str, value: str) -> dict[str, Any]:
    start = text.index(value)
    end = start + len(value)
    return {"character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(text[:start].encode()), len(text[:end].encode())],
            "sha256": hashlib.sha256(value.encode()).hexdigest()}


def main() -> None:
    receipt_path = ART / "humor-mechanics-batch2-development-pilot10-candidate01-g02c-conformance-receipt-v5-2.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot10-candidate01-g02c-review-v5-2.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02_COMMIT, "HEAD")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode("utf-8")
    g02 = git_json(G02_COMMIT, G02_PATH)
    packet = git_json(PACKET_COMMIT, PACKET_PATH)
    schema = git_json(PACKET_COMMIT, SCHEMA_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] == "6ee68cf88584afec9d1f4cccb198e96d99045f142c9466d5a51f1c7e41102187", "G02")
    require(g02["candidate_git_blob_oid_sha1"] == "8dfbc43c94190e5b0fca48d6bcd28adf55c21391", "candidate blob")
    require(hashlib.sha256(candidate).hexdigest() == "013c70e3c15833e789592915f5f31b62eeaed5c1148ff6b6f78607cb0c907464", "candidate")
    require(packet["constructor_facing_packet_identity"] == "7d894969dfeed0703ee31f4fe3223ef9dfbdd3fbe873f2ac6d6e02054e8694aa", "packet")
    require(packet["typed_plan_commitment"] == "0bd5a77f4ee4d05784d9722fdb9991302e144c6e45511861063bdce8a382432e", "typed plan")
    require(obligation["obligation_instance_identity"] == "6aad43d4814e56aa7df3f747caa79e5809ebed19328365542de4321c33ddd97d", "obligation")
    require(obligation["obligation_version"] == "DEVELOPMENT_TRANSFORMATION_V5_2_01", "version")
    require(schema["schema_identity"] == "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b", "schema")

    selected_fact = "Dacă greutatea corespunde valorii înscrise în document și numărul de pe etichetă corespunde celui din document, lada este înregistrată cu eticheta APROBAT și este mutată în zona de depozitare destinată materialelor horticole."
    node1 = "Într-un registru imaginar, aprobarea și mutarea lăzii, dacă greutatea și numărul etichetei corespund documentului, pornesc regula depozitului: orice spațiu care primește lada devine material horticol provizoriu."
    node2 = "Regula depozitului prinde astfel zona destinată materialelor horticole în propriul inventar și o transformă în zona devenită material horticol."
    terminal = "Zona devenită material horticol aplică apoi aprobarea și mutarea lăzii chiar depozitului: depozitul primește eticheta APROBAT și este mutat în el însuși."
    require(text == " ".join((selected_fact, node1, node2, terminal)) + "\n", "surface")
    spans = {"selected_fact": surface_span(text, selected_fact), "node_L1": surface_span(text, node1),
             "node_L2": surface_span(text, node2), "node_RESULT": surface_span(text, terminal)}

    nodes = {
        "L1": {"materially_instantiated": True, "actor": "approval and movement of the crate under both matching conditions",
               "relation": "starts an imaginary storage rule", "patient_or_result": "a receiving space becomes provisional horticultural material",
               "operand_continuity": "PASS_FROM_EXACT_P3", "local_recoverability": "PASS"},
        "L2": {"materially_instantiated": True, "actor": "the storage rule produced by L1",
               "relation": "applies to the horticultural-storage zone that receives the crate",
               "patient_or_result": "the zone becomes horticultural material", "operand_continuity": "PASS_L1_TO_L2",
               "local_recoverability": "PASS"},
        "RESULT": {"materially_instantiated": True, "actor": "the zone classified as horticultural material by L2",
                   "relation": "purports to apply the crate approval/movement operation to the depot",
                   "patient_or_result": "the depot is approved and moved into itself", "operand_continuity": "LEXICALLY_PRESENT_ROLE_INCOMPATIBLE",
                   "local_recoverability": "FAIL_NO_RULE_OR_PRIOR_RELATION_LICENSES_AGENTIVE_PROCEDURE_APPLICATION"},
    }
    edges = {
        "P3_TO_L1": {"materially_instantiated": True, "recoverable": True, "necessary": True,
                      "non_arbitrary": True, "finding": "The destination-for-horticultural-material relation supplies the imaginary receiving-space rule."},
        "L1_TO_L2": {"materially_instantiated": True, "recoverable": True, "necessary": True,
                      "non_arbitrary": True, "finding": "The zone receives the crate and therefore satisfies L1's expressly stated rule."},
        "L2_TO_RESULT": {"materially_instantiated": True, "recoverable": True, "necessary": False,
                         "non_arbitrary": False, "finding": "Classification as horticultural material does not entail agency or authority to apply the crate procedure to the depot."},
    }
    predicates = {
        "COMPLETE_REQUIRED_MULTI_LINK_CAUSAL_SPINE_RECOVERABLE": False,
        "EVERY_REQUIRED_CAUSAL_NODE_MATERIALLY_INSTANTIATED": True,
        "EVERY_REQUIRED_CAUSAL_EDGE_MATERIALLY_INSTANTIATED": True,
        "TYPED_OPERANDS_RECOVERABLE_AND_CONTINUOUS_WITH_ROLE_COMPATIBILITY": False,
        "EVERY_LINK_NECESSARY_AND_NON_ARBITRARY": False,
        "EXACTLY_ONE_EXPLICIT_TERMINAL_RESULT_RECOVERABLE": True,
        "NO_PLACEHOLDER_SUMMARY_META_ASSERTION_OR_COLLAPSED_RELATION": True,
        "NO_INSTRUCTION_GOVERNANCE_OR_PLAN_LANGUAGE_TRANSFER": True,
        "QUALIFICATION_AND_FICTIONAL_MARKING_RETAINED": True,
        "NO_FORBIDDEN_OPERATION_BECOMES_THE_RESULT_ENGINE": False,
    }
    failure = {
        "classification": "TERMINAL_EDGE_NON_ARBITRARY_CAUSAL_CONTINUITY_FAILURE",
        "earliest_failed_link": "L2_TO_TERMINAL_RESULT",
        "observed_gap": "The surface makes the newly classified zone perform the crate approval/movement procedure on the depot without a preceding rule that produces that agency or role.",
        "typed_operand_finding": "INVENTED_RELATION_2_IS_LEXICALLY_CONTINUOUS_BUT_CHANGES_FROM_CLASSIFIED_PATIENT_STATE_TO_AGENTIVE_PROCEDURE_APPLIER",
        "necessity_finding": "The terminal action can be replaced or removed without contradicting L2, so it is not a necessary consequence of the recovered prior relation.",
        "forbidden_operation_finding": "The payoff materially relies on nonhuman agency/personification and role reversal, which the obligation forbids as the realization engine.",
        "pre_emission_receipt_status": "PRESERVED_AS_FORMAL_WITNESS_PROVENANCE_NOT_ACCEPTED_AS_INDEPENDENT_SEMANTIC_PROOF",
        "candidate_repair_performed": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot10-g02c-conformance-receipt-v5-2", "schema_version": "5.2.0",
        "candidate_identity": g02["candidate_identity"], "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
        "constructor_contract_identity": packet["constructor_contract_identity"],
        "constructor_implementation_identity": packet["constructor_implementation_identity"],
        "realization_provider_identity": packet["realization_provider_identity"],
        "candidate_emitter_identity": packet["candidate_emitter_identity"],
        "typed_plan_commitment": packet["typed_plan_commitment"],
        "conformance_schema_identity": schema["schema_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "obligation_instance_identity": obligation["obligation_instance_identity"], "obligation_version": obligation["obligation_version"],
        "selected_proposition_id": "P3", "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "fragment_collision_receipt_identity": g02["fragment_collision_binding"]["receipt_identity"],
        "pre_emission_conformance_provenance": "PASS_PRESERVED_NOT_USED_AS_SUFFICIENT_SEMANTIC_EVIDENCE",
        "surface_components": spans, "independently_recovered_nodes": nodes, "independently_recovered_edges": edges,
        "required_predicates": predicates, "failure": failure,
        "sealed_mapping_accessed": False, "mechanism_adjudication_performed": False,
        "romanian_naturalness_adjudicated": False, "voice_adjudicated": False,
        "verdict": "FAIL_TERMINAL_EDGE_NON_ARBITRARY_CAUSAL_CONTINUITY",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT10_G02C_CONFORMANCE_RECEIPT_V5_2", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot10-candidate-g02c-review-v5-2", "schema_version": "5.2.0",
        "candidate_identity": g02["candidate_identity"], "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "creative_premise_family_id": g02["creative_premise_family_id"], "creative_marker_family_id": g02["creative_marker_family_id"],
        "g02_commit": G02_COMMIT, "g02_receipt_identity": g02["g02_receipt_identity"],
        "conformance_receipt_identity": receipt_id,
        "predicate_verification": "FAIL_FOUR_OF_TEN_SEMANTIC_POSTCONSTRUCTION_CONFORMANCE_PREDICATES",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED", "sealed_mapping_accessed": False,
        "g03_performed": False, "romanian_naturalness_review_performed": False, "voice_review_performed": False,
        "candidate_modified": False, "g02c_verdict": receipt_core["verdict"],
        "disposition": "G02C_REJECTED_STOP_NO_REPAIR", "g03_eligibility": False,
        "eligibility": "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL",
        "authority_matrix": {key: False for key in ("g03_mechanism_recovery", "g03b", "g03c",
                              "g04a_romanian_naturalness", "voice_review", "repair", "rewrite", "regeneration",
                              "additional_construction", "owner_review", "g04b_pool_certification", "model_exposure",
                              "training", "runtime_integration", "production_routing")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT10_G02C_REVIEW_V5_2", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": review["g02c_verdict"], "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"], "g03_eligibility": False,
                      "next_action": "FREEZE_NONPOSITIVE_G02C_REJECTION_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
