"""Mechanism-neutral G02C review for Pilot 06 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "cc61efc4dc6d90016f72fbd1e92111eb83751424"
ASSIGNMENT_COMMIT = "c2aea939a22e6e0dd3e33f05e43a8d1f0796e4d4"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot06-constructor-facing-rebalancing-assignment-proposal-v2.json"


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
    receipt_path = ART / "humor-mechanics-batch2-development-pilot06-candidate01-g02c-conformance-receipt-v2.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot06-candidate01-g02c-review-v2.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C exists")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02_COMMIT, "HEAD")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode()
    g02 = git_json(G02_COMMIT, G02_PATH)
    packet = git_json(ASSIGNMENT_COMMIT, PACKET_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] == "714cbc8caf038088f5770d67950bbe703689a462b0dcfcd23c9babdd28972909", "G02")
    require(hashlib.sha256(candidate).hexdigest() == "e00b1b83507ece1808445a3f6cfd07286ee20eecc6f4208d9aa4940ab2fbc1a9", "candidate")
    require(packet["constructor_facing_packet_identity"] == "206645473d3dd479ea0cdadc88fff9f4f8d487e0ecdde50d9618d288c10cff86", "packet")
    require(obligation["obligation_instance_identity"] == "0c1f9e12d66d64294a1023e7da2707e397cc8c7714b09c04e84be8713f28e40a", "obligation")
    require(obligation["obligation_version"] == "REVERSE_DISCLOSURE_DEPENDENCY_V2", "version")
    result = "calendarul bibliotecii rămâne fără o zi"
    step1 = "data a fost absorbită de registru"
    step2 = "deoarece apare lângă mențiunea „verificat”"
    factual = packet["exact_authorized_visible_context_utf8"]
    require(all(value in text for value in (result, step1, step2, factual)), "components")
    spans = {key: surface_span(text, value) for key, value in (("result", result), ("step1", step1), ("step2", step2), ("factual", factual))}
    require(spans["result"]["character_coordinates"][0] < spans["step1"]["character_coordinates"][0]
            < spans["step2"]["character_coordinates"][0] < spans["factual"]["character_coordinates"][0], "reverse order")
    require(text.startswith("Într-o continuare imaginară, "), "fiction marking")
    governance_tokens = ("obligație", "cerință", "propoziție autorizată", "legătură succesivă", "mecanism", "verificarea rezultatului")
    require(not any(token in text.casefold() for token in governance_tokens), "instruction transfer")
    predicates = {
        "EXACT_SELECTED_PROPOSITION_PRESERVED": True,
        "INVENTED_RESULT_PRESENTED_FIRST": True,
        "TWO_REVERSE_LINKS_PRESENT_IN_ORDER": True,
        "RESULT_DEPENDS_ON_IMMEDIATE_ABSORPTION_LINK": True,
        "ABSORPTION_LINK_DEPENDS_ON_DATE_AND_STATUS_COLOCATION": True,
        "FINAL_LINK_RECOVERABLE_FROM_SELECTED_P3_RELATION": True,
        "ALL_REFERENCES_AND_OPERANDS_BOUND": True,
        "EACH_STEP_NON_ARBITRARY": True,
        "COMPLETE_REVERSE_DEPENDENCY_CHAIN": True,
        "INVENTED_SEQUENCE_EXPLICITLY_NONFACTUAL": True,
        "FORBIDDEN_RECLASSIFICATION_HUMAN_AGENCY_AND_META_LANGUAGE_ABSENT": True,
    }
    dependency = {
        "ordered_chain": ["FICTIONAL_MISSING_CALENDAR_DAY", "FICTIONAL_DATE_ABSORBED_INTO_REGISTER", "DATE_ADJACENT_TO_VERIFIED_STATUS", "EXACT_P3_REGISTER_RELATION"],
        "result_to_step1": "PASS_REMOVING_ABSORPTION_REMOVES_EXPLANATION_FOR_MISSING_DAY",
        "step1_to_step2": "PASS_ABSORPTION_IS_LOCALLY_GROUNDED_BY_DATE_STATUS_COLOCATION",
        "step2_to_selected_fact": "PASS_EXACT_P3_BINDS_VERIFIED_STATUS_AND_CONTROL_DATE_IN_REGISTER",
        "arbitrary_substitution": False,
        "unbound_operand_or_reference": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot06-g02c-conformance-receipt-v2",
        "schema_version": "2.0.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"],
        "obligation_instance_identity": obligation["obligation_instance_identity"],
        "obligation_version": obligation["obligation_version"],
        "selected_proposition_id": "P3",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "surface_components": spans,
        "dependency_trace": dependency,
        "required_predicates": predicates,
        "naturalness_precheck": {"instruction_or_governance_language_transferred": False,
                                 "materially_procedural_abstract_register": False,
                                 "does_not_replace_blind_g04a": True},
        "verdict": "PASS",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT06_G02C_CONFORMANCE_RECEIPT_V2", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot06-candidate-g02c-review-v2",
        "schema_version": "2.0.0",
        "candidate_identity": g02["candidate_identity"],
        "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "creative_premise_family_id": g02["creative_premise_family_id"],
        "g02_commit": G02_COMMIT,
        "g02_receipt_identity": g02["g02_receipt_identity"],
        "conformance_receipt_identity": receipt_id,
        "predicate_verification": "PASS_ALL_REVERSE_DISCLOSURE_DEPENDENCY_V2_PREDICATES",
        "naturalness_precheck": "PASS_NO_INSTRUCTION_TO_SURFACE_TRANSFER",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED",
        "sealed_mapping_accessed": False,
        "g03_performed": False,
        "candidate_modified": False,
        "g02c_verdict": "PASS",
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_BLIND_G03_MECHANISM_RECOVERY",
        "authority_matrix": {key: False for key in ("g03_mechanism_recovery", "repair", "rewrite", "regeneration", "owner_review", "training", "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT06_G02C_REVIEW_V2", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": "PASS", "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"], "next_gate": "BLIND_G03_MECHANISM_RECOVERY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
