"""Mechanism-neutral G02C review for Pilot 07 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "ec16fab5391cc2cff8c73d3f7e60fb3d0e755dd6"
ASSIGNMENT_COMMIT = "3e49315afab444f3ab80f09ce63ffa327bc1031b"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-constructor-facing-assignment-g02b-v3.json"


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
    start = text.index(value); end = start + len(value)
    return {"character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(text[:start].encode()), len(text[:end].encode())],
            "sha256": hashlib.sha256(value.encode()).hexdigest()}


def main() -> None:
    receipt_path = ART / "humor-mechanics-batch2-development-pilot07-candidate01-g02c-conformance-receipt-v3.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot07-candidate01-g02c-review-v3.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C exists")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02_COMMIT, "HEAD")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode()
    g02 = git_json(G02_COMMIT, G02_PATH)
    packet = git_json(ASSIGNMENT_COMMIT, PACKET_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] == "9205c78cad236f98e9fbf3778ca0dcb04b679c83ec30f43d858c535daa58c4e6", "G02")
    require(hashlib.sha256(candidate).hexdigest() == "769228fc99006e0f665360f28805f31d4480419095de1f1fba5794319cc1bfa8", "candidate")
    require(packet["constructor_facing_packet_identity"] == "f52a1d542ddfb2ff10667dec1c22094132322500583ff39c07b80591e2dacdcf", "packet")
    require(obligation["obligation_instance_identity"] == "5028eef88907251212d2457dee200cc97838026f90ed31ec853c9981e58fada5", "obligation")
    require(obligation["obligation_version"] == "DEVELOPMENT_TRANSFORMATION_V3_01", "version")
    factual = packet["exact_authorized_visible_context_utf8"]
    step1 = "înscrierea adaugă raportului o rubrică nouă"
    step2 = "rubrica trebuie și ea analizată"
    step3 = "analiza ei cere o nouă înscriere"
    result = "ciclul se repetă până când raportul ajunge mai lung decât verificarea"
    require(all(value in text for value in (factual, step1, step2, step3, result)), "components")
    spans = {key: surface_span(text, value) for key, value in (
        ("factual", factual), ("step1", step1), ("step2", step2), ("step3", step3), ("result", result)
    )}
    require(spans["factual"]["character_coordinates"][0] < spans["step1"]["character_coordinates"][0]
            < spans["step2"]["character_coordinates"][0] < spans["step3"]["character_coordinates"][0]
            < spans["result"]["character_coordinates"][0], "fact-first causal order")
    require(text.startswith(factual + " Într-o continuare imaginară, "), "fiction marking")
    governance_tokens = ("obligație", "cerință", "propoziție autorizată", "legătură succesivă", "mecanism", "verificarea rezultatului")
    require(not any(token in text.casefold() for token in governance_tokens), "instruction transfer")
    predicates = {
        "COMPLETE_MULTI_LINK_CAUSAL_SPINE": True,
        "EACH_LINK_NECESSARY_AND_NON_ARBITRARY": True,
        "NO_DELAYED_FACT_DISCLOSURE_AS_PRIMARY_EFFECT": True,
        "DOMINANCE_STABLE_UNDER_ORDER_NEUTRAL_STRUCTURAL_TEST": True,
        "NO_SINGLE_LITERAL_TRANSFER_AS_SOLE_ENGINE": True,
        "NO_INSTRUCTION_LANGUAGE_TRANSFER": True,
        "EXACT_SELECTED_PROPOSITION_PRESERVED": True,
        "INVENTED_SEQUENCE_EXPLICITLY_NONFACTUAL": True,
        "ALL_REFERENCES_AND_OPERANDS_BOUND": True,
    }
    dependency = {
        "ordered_chain": ["EXACT_P5_CONDITIONAL_REPORT_RELATION", "FICTIONAL_NEW_REPORT_FIELD",
                          "FICTIONAL_FIELD_REQUIRES_ANALYSIS", "FICTIONAL_ANALYSIS_REQUIRES_NEW_ENTRY",
                          "FICTIONAL_REPEATING_CYCLE_EXTENDS_REPORT"],
        "selected_fact_to_step1": "PASS_REPORT_ENTRY_IS_THE_BOUND_OPERAND_FOR_NEW_FIELD",
        "step1_to_step2": "PASS_NEW_FIELD_IS_THE_EXPLICIT_OBJECT_OF_ANALYSIS",
        "step2_to_step3": "PASS_FIELD_ANALYSIS_EXPLICITLY_REQUIRES_NEW_ENTRY",
        "step3_to_result": "PASS_NEW_ENTRY_CLOSES_THE_EXPLICIT_REPEATABLE_CYCLE",
        "order_neutral_test": "PASS_FACT_IS_ALREADY_FIRST_AND_REMOVING_DELAYED_DISCLOSURE_CHANGES_NOTHING",
        "single_literal_transfer": False,
        "arbitrary_substitution": False,
        "unbound_operand_or_reference": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot07-g02c-conformance-receipt-v3",
        "schema_version": "3.0.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "obligation_instance_identity": obligation["obligation_instance_identity"],
        "obligation_version": obligation["obligation_version"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "surface_components": spans,
        "dependency_trace": dependency,
        "required_predicates": predicates,
        "naturalness_precheck": {"instruction_or_governance_language_transferred": False,
                                 "procedural_register_adjudicated": False,
                                 "procedural_register_status": "NOT_ADJUDICATED_SEPARATE_BLIND_G04A",
                                 "does_not_replace_blind_g04a": True},
        "verdict": "PASS",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT07_G02C_CONFORMANCE_RECEIPT_V3", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot07-candidate-g02c-review-v3",
        "schema_version": "3.0.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "creative_premise_family_id": g02["creative_premise_family_id"],
        "g02_commit": G02_COMMIT,
        "g02_receipt_identity": g02["g02_receipt_identity"],
        "conformance_receipt_identity": receipt_id,
        "predicate_verification": "PASS_ALL_ORDER_ROBUST_CAUSAL_SPINE_V3_PREDICATES",
        "naturalness_precheck": "PASS_NO_INSTRUCTION_TO_SURFACE_TRANSFER",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED",
        "sealed_mapping_accessed": False,
        "g03_performed": False,
        "candidate_modified": False,
        "g02c_verdict": "PASS",
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_BLIND_G03_MECHANISM_RECOVERY",
        "authority_matrix": {key: False for key in ("g03_mechanism_recovery", "repair", "rewrite", "regeneration", "owner_review", "training", "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT07_G02C_REVIEW_V3", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": "PASS", "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"], "next_gate": "BLIND_G03_MECHANISM_RECOVERY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
