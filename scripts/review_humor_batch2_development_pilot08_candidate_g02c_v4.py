"""Mechanism-neutral Governance V4 G02C review for Pilot 08 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "7381e7bd2b06d7478b7e9cb36f3221221a0f423e"
PACKET_COMMIT = "c33e82cac589b0fdf036331f7bf6cec97fe75106"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-constructor-facing-assignment-g02b-v4.json"


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


def span(text: str, value: str, occurrence: int = 0) -> dict[str, Any]:
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(value, start + 1)
    end = start + len(value)
    return {
        "character_coordinates": [start, end],
        "utf8_byte_coordinates": [len(text[:start].encode()), len(text[:end].encode())],
        "sha256": hashlib.sha256(value.encode()).hexdigest(),
    }


def main() -> None:
    receipt_path = ART / "humor-mechanics-batch2-development-pilot08-candidate01-g02c-conformance-receipt-v4.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot08-candidate01-g02c-review-v4.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G02_COMMIT, "HEAD")

    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode("utf-8")
    g02 = git_json(G02_COMMIT, G02_PATH)
    packet = git_json(PACKET_COMMIT, PACKET_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS", "G02 verdict")
    require(g02["g02_receipt_identity"] == "dc3151a1c6d9f8f41ef62f40a27d3e8c1bc764ad11456b187027b82f974bd4ae", "G02 receipt")
    require(g02["candidate_git_blob_oid_sha1"] == "679ad8c85f55f002523657baf531587694f5f607", "candidate blob")
    require(hashlib.sha256(candidate).hexdigest() == "bc71da32026e9173440a494279fd4dca752cfc8c5547abcaa1ad922bdda0368a", "candidate")
    require(packet["constructor_facing_packet_identity"] == "4e812e402c2d56f5b95f5aa60bd09630117de72377d2a6bb8da0e446ac2634ae", "packet")
    require(obligation["obligation_instance_identity"] == "d2d6ad3d20e577c5834f7534028eb21e22f378b330a1607d27eacaa86e2f8876", "obligation")
    require(obligation["obligation_version"] == "DEVELOPMENT_TRANSFORMATION_V4_01", "version")

    factual = packet["exact_authorized_visible_context_utf8"]
    marker = "În variantă inventată a regulăii"
    repeated_relation = "este trecută în fișa de intervenție pentru verificarea ulterioară a electrovanei, cablajului sau circuitului de comandă"
    failed_operand = "în fișa de intervenție pentru verificarea ulterioară a electrovanei, cablajului sau circuitului de comandă. mută controlul"
    later_link = "regulăa se aplică din nou"
    result = "controlul ajunge să verifice chiar regulăa"
    require(text.startswith(factual + " "), "fact first")
    require(all(value in text for value in (marker, repeated_relation, failed_operand, later_link, result)), "surface components")

    spans = {
        "factual": span(text, factual),
        "creative_marker": span(text, marker),
        "repeated_relation": span(text, repeated_relation, 1),
        "first_claimed_link_with_unbound_actor": span(text, failed_operand),
        "later_claimed_link": span(text, later_link),
        "claimed_result": span(text, result),
    }
    predicates = {
        "EXACT_SELECTED_PROPOSITION_PRESERVED": True,
        "FACT_AVAILABLE_BEFORE_RETROSPECTIVE_READING_CHANGE": True,
        "INVENTED_SEQUENCE_EXPLICITLY_NONFACTUAL": True,
        "AT_LEAST_TWO_DISTINCT_LOCALLY_RECOVERABLE_LINKS": False,
        "EACH_LINK_NECESSARY_AND_NON_ARBITRARY": False,
        "ALL_REFERENCES_AND_OPERANDS_BOUND": False,
        "COMPLETE_MULTI_LINK_CAUSAL_SPINE": False,
        "CONSEQUENCE_DEPENDS_ON_COMPLETE_CHAIN": False,
        "NO_DELAYED_FACT_DISCLOSURE_AS_PRIMARY_EFFECT": True,
        "NO_SINGLE_LITERAL_TRANSFER_AS_SOLE_ENGINE": True,
        "NO_INSTRUCTION_LANGUAGE_TRANSFER": True,
        "FRAGMENT_COLLISION_GATE_PASSED": True,
    }
    dependency = {
        "selected_fact": "PASS_EXACT_P5_CONDITIONAL_RECORDING_AND_LATER_CHECK_RELATION",
        "fact_to_repeated_relation": "FAIL_REPETITION_RESTATES_P5_WITHOUT_ESTABLISHING_A_DISTINCT_CONSEQUENCE",
        "repeated_relation_to_control_return": "FAIL_PREPOSITIONAL_LOCATION_PURPORTEDLY_MOVES_CONTROL_WITHOUT_A_BOUND_ACTOR_OR_HEAD",
        "control_return_to_rule_reapplication": "NOT_SUFFICIENT_TO_CURE_EARLIER_OPERAND_CLOSURE_FAILURE",
        "rule_reapplication_to_result": "LOCALLY_STATED_BUT_NOT_CONNECTED_BY_A_COMPLETE_RECOVERABLE_CHAIN",
        "unbound_operand_or_reference": True,
        "arbitrary_or_substitutable_link": True,
        "fact_first_order": True,
        "single_literal_transfer": False,
    }
    failure = {
        "classification": "UNBOUND_OPERAND_AND_INCOMPLETE_MULTI_LINK_CAUSAL_SPINE",
        "earliest_failed_link": "FIRST_INVENTED_RELATION_TO_CONTROL_RETURN",
        "observed_gap": "The phrase beginning 'în fișa de intervenție' is a prepositional location/purpose phrase, yet the surface makes it the apparent mover of 'controlul' without supplying a bound actor or grammatical head.",
        "consequence": "The first distinct invented dependency is not locally recoverable, so later rule reapplication and self-verification cannot establish a complete necessary chain back to P5.",
        "naturalness_adjudication_required_for_failure": False,
        "mechanism_label_required_for_failure": False,
        "candidate_repair_performed": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot08-g02c-conformance-receipt-v4",
        "schema_version": "4.0.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
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
            "instruction_or_governance_language_transferred": False,
            "romanian_naturalness_adjudicated": False,
            "voice_adjudicated": False,
            "does_not_replace_separate_quality_gates": True,
        },
        "verdict": "FAIL_UNBOUND_OPERAND_AND_INCOMPLETE_MULTI_LINK_CAUSAL_SPINE",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT08_G02C_CONFORMANCE_RECEIPT_V4", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot08-candidate-g02c-review-v4",
        "schema_version": "4.0.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "creative_premise_family_id": g02["creative_premise_family_id"],
        "creative_marker_family_id": g02["creative_marker_family_id"],
        "g02_commit": G02_COMMIT,
        "g02_receipt_identity": g02["g02_receipt_identity"],
        "conformance_receipt_identity": receipt_id,
        "predicate_verification": "FAIL_FIVE_REQUIRED_CAUSAL_DEPENDENCY_AND_OPERAND_CLOSURE_PREDICATES",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED",
        "sealed_mapping_accessed": False,
        "g03_performed": False,
        "romanian_naturalness_review_performed": False,
        "voice_review_performed": False,
        "candidate_modified": False,
        "g02c_verdict": receipt_core["verdict"],
        "disposition": "G02C_REJECTED_STOP_NO_REPAIR",
        "eligibility": "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL",
        "authority_matrix": {key: False for key in (
            "g03_mechanism_recovery", "g04a_romanian_naturalness", "voice_review", "repair", "rewrite",
            "regeneration", "owner_review", "training", "runtime_integration", "production_routing",
            "g04b_pool_certification",
        )},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT08_G02C_REVIEW_V4", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "g02c_verdict": review["g02c_verdict"],
        "conformance_receipt_identity": receipt_id,
        "g02c_review_identity": review["g02c_review_identity"],
        "next_action": "FREEZE_NONPOSITIVE_G02C_REJECTION_SEPARATELY_AUTHORIZED",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
