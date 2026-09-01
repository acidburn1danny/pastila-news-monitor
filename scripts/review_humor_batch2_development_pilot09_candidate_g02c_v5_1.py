"""Mechanism-neutral Governance V5.1 G02C review for Pilot 09 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "9bab6b404e6fba63bc215a2deee990369c7fbe20"
PACKET_COMMIT = "2a8f40366a5b215cbf27e6bb55f7ac478682c09f"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-facing-assignment-g02b-v5-1.json"
SCHEMA_PATH = "docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json"


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


def span(text: str, value: str) -> dict[str, Any]:
    start = text.index(value)
    end = start + len(value)
    return {
        "character_coordinates": [start, end],
        "utf8_byte_coordinates": [len(text[:start].encode()), len(text[:end].encode())],
        "sha256": hashlib.sha256(value.encode()).hexdigest(),
    }


def main() -> None:
    receipt_path = ART / "humor-mechanics-batch2-development-pilot09-candidate01-g02c-conformance-receipt-v5-1.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot09-candidate01-g02c-review-v5-1.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G02_COMMIT, "HEAD")

    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode("utf-8")
    g02 = git_json(G02_COMMIT, G02_PATH)
    packet = git_json(PACKET_COMMIT, PACKET_PATH)
    schema = git_json(PACKET_COMMIT, SCHEMA_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS", "G02 verdict")
    require(g02["g02_receipt_identity"] == "f0bbb5887872c91909cf9467677a13d970319dafdd1bc42f511b7e2bf71f0a66", "G02 receipt")
    require(g02["candidate_git_blob_oid_sha1"] == "fd1c7c024523faf63efe610849620364638a48b3", "candidate blob")
    require(hashlib.sha256(candidate).hexdigest() == "3249775af5b93a68f00ab1e8217652a1411db03d61a40dfbe1e1fa3f7cd7e307", "candidate")
    require(packet["constructor_facing_packet_identity"] == "f59803859660dcd29d7934873c80ce9febbf16c422d937ab4c8dd7a214c3446d", "packet")
    require(packet["constructor_implementation_generation"] == "5.1", "generation")
    require(packet["typed_plan_commitment"] == "016a0f20d3fcbad3446439a6456577344f3b19086fe9fd174011615e2d0870de", "typed plan")
    require(obligation["obligation_instance_identity"] == "b6c600d6cb4cef27d02fcffe0e978a2c9f694f33351ed630c4bdf3b35513098b", "obligation")
    require(obligation["obligation_version"] == "DEVELOPMENT_TRANSFORMATION_V5_01", "version")
    require(schema["schema_identity"] == "29d7b0f97008ad38e64b8e966f398d829a66299ec805290ebbec3f92848efab6", "schema")
    require("FAIL_INCOMPLETE_CAUSAL_SPINE" in schema["allowed_verdicts"], "allowed verdict")

    factual = "Dacă senzorul nu detectează coletul sau semnalul nu ajunge la unitatea de control, banda nu pornește automat."
    marker = "Într-un cadru explicit imaginar"
    claimed_links = "relația continuă prin două consecințe locale"
    claimed_dependency = "ultima depinde de întregul traseu inventat"
    require(text == factual + " " + marker + ", " + claimed_links + ", iar " + claimed_dependency + ".\n", "surface")

    spans = {
        "selected_fact": span(text, factual),
        "creative_marker": span(text, marker),
        "uninstantiated_link_count_claim": span(text, claimed_links),
        "uninstantiated_dependency_claim": span(text, claimed_dependency),
    }
    predicates = {
        "COMPLETE_MULTI_LINK_CAUSAL_SPINE": False,
        "AT_LEAST_TWO_DISTINCT_NON_RESTATEMENT_LINKS": False,
        "EACH_LINK_NECESSARY_AND_NON_ARBITRARY": False,
        "ALL_REFERENCES_AND_OPERANDS_ROLE_COMPATIBLE_AND_BOUND": False,
        "NO_TERMINAL_PUNCTUATION_SPLIT_WITHIN_A_CLAIMED_LINK": True,
        "NO_DELAYED_FACT_DISCLOSURE_AS_PRIMARY_EFFECT": True,
        "NO_SINGLE_LITERAL_TRANSFER_AS_SOLE_ENGINE": True,
        "NO_INSTRUCTION_LANGUAGE_TRANSFER": False,
    }
    require(set(predicates) == set(schema["required_postconstruction_g02c_predicates"]), "predicate coverage")
    dependency = {
        "selected_fact": "PASS_EXACT_P5_TRIGGER_TO_AUTOMATIC_NONSTART_RELATION",
        "selected_fact_to_first_invented_link": "FAIL_NO_INVENTED_EVENT_RELATION_OR_RESULT_IS_SURFACE_INSTANTIATED",
        "first_to_second_invented_link": "FAIL_ONLY_A_NUMERIC_CLAIM_OF_TWO_CONSEQUENCES_IS_PRESENT",
        "second_link_to_result": "FAIL_NO_CONCRETE_TERMINAL_CONSEQUENCE_IS_PRESENT",
        "typed_static_plan_commitment": "PASS_FROZEN_PRECONSTRUCTION_BUT_NOT_SURFACE_EVIDENCE",
        "surface_operand_dataflow": "FAIL_NO_LINK_LEVEL_ACTOR_PATIENT_PREDICATE_OR_PRODUCED_OPERAND_CAN_BE RECOVERED".replace(" ", "_"),
        "surface_link_necessity": "FAIL_UNTESTABLE_WITHOUT_INSTANTIATED_LINKS",
        "fact_first_order": True,
        "single_literal_transfer": False,
    }
    failure = {
        "classification": "INCOMPLETE_CAUSAL_SPINE",
        "earliest_failed_link": "SELECTED_FACT_TO_FIRST_INVENTED_CONSEQUENCE",
        "observed_gap": "The surface asserts that two local consequences and a complete path exist but supplies neither consequence, no link predicate, and no produced operand.",
        "consequence": "No proposition-derived multi-link spine, typed surface dataflow, link necessity, or non-arbitrariness can be independently recovered from the immutable candidate.",
        "instruction_language_transfer": "The phrases 'two local consequences' and 'complete invented path' restate obligation structure instead of realizing it.",
        "naturalness_adjudication_required_for_failure": False,
        "mechanism_label_required_for_failure": False,
        "candidate_repair_performed": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot09-g02c-conformance-receipt-v5-1",
        "schema_version": "5.1.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
        "constructor_contract_identity": packet["constructor_contract_identity"],
        "constructor_implementation_identity": packet["constructor_implementation_identity"],
        "constructor_source_compatibility_identity": packet["constructor_source_compatibility_identity"],
        "typed_plan_commitment": packet["typed_plan_commitment"],
        "conformance_schema_identity": schema["schema_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "obligation_instance_identity": obligation["obligation_instance_identity"],
        "obligation_version": obligation["obligation_version"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "fragment_collision_receipt_identity": g02["fragment_collision_binding"]["receipt_identity"],
        "surface_components": spans,
        "dependency_trace": dependency,
        "required_predicates": predicates,
        "failure": failure,
        "naturalness_precheck": {
            "instruction_or_governance_language_transferred": True,
            "romanian_naturalness_adjudicated": False,
            "voice_adjudicated": False,
            "does_not_replace_separate_quality_gates": True,
        },
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "verdict": "FAIL_INCOMPLETE_CAUSAL_SPINE",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT09_G02C_CONFORMANCE_RECEIPT_V5_1", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot09-candidate-g02c-review-v5-1",
        "schema_version": "5.1.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "creative_premise_family_id": g02["creative_premise_family_id"],
        "creative_marker_family_id": g02["creative_marker_family_id"],
        "g02_commit": G02_COMMIT,
        "g02_receipt_identity": g02["g02_receipt_identity"],
        "conformance_receipt_identity": receipt_id,
        "predicate_verification": "FAIL_FIVE_OF_EIGHT_POSTCONSTRUCTION_CONFORMANCE_PREDICATES",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED",
        "sealed_mapping_accessed": False,
        "g03_performed": False,
        "romanian_naturalness_review_performed": False,
        "voice_review_performed": False,
        "candidate_modified": False,
        "g02c_verdict": receipt_core["verdict"],
        "disposition": "G02C_REJECTED_STOP_NO_REPAIR",
        "g03_eligibility": False,
        "eligibility": "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL",
        "authority_matrix": {key: False for key in (
            "g03_mechanism_recovery", "g03b", "g03c", "g04a_romanian_naturalness", "voice_review",
            "repair", "rewrite", "regeneration", "owner_review", "training", "runtime_integration",
            "production_routing", "g04b_pool_certification",
        )},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT09_G02C_REVIEW_V5_1", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": review["g02c_verdict"], "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"], "g03_eligibility": False,
                      "next_action": "FREEZE_NONPOSITIVE_G02C_REJECTION_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
