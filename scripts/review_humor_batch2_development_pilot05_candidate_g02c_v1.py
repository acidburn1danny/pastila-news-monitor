"""Mechanism-neutral G02C review for Pilot 05 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "9794f0e9ff7ca227d2eae6852f4b2f4d67fc6806"
ASSIGNMENT_COMMIT = "def90e29e81f42e41e3cb77417000710207dc88a"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02-v1.json"
PACKET_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-constructor-facing-rebalancing-assignment-proposal-v1.json"


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
    receipt_path = ART / "humor-mechanics-batch2-development-pilot05-candidate01-g02c-conformance-receipt-v1.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot05-candidate01-g02c-review-v1.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02_COMMIT, "HEAD")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    text = candidate.decode("utf-8")
    g02 = git_json(G02_COMMIT, G02_PATH)
    packet = git_json(ASSIGNMENT_COMMIT, PACKET_PATH)
    obligation = packet["unlabeled_operational_obligation"]
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] == "02edafd3200d39fcf842e570a8ab3c824107e893cbbe5c01742d70e1f0cadab3", "G02")
    require(hashlib.sha256(candidate).hexdigest() == "8030222614461de66246eb9f2a14d1230e271b327007092f30f216f55a0d7166", "candidate")
    require(packet["constructor_facing_packet_identity"] == "116febfa5e3953741e7afbbddc78eaecf09b33dbdad495d3f3019903b8a56b2a", "packet")
    require(obligation["obligation_instance_identity"] == "5b876dc08d35f154196d00d4a5f73c6d68b268061c4144e2971f7aca32395228", "obligation")
    require(obligation["obligation_version"] == "REVERSE_DISCLOSURE_DEPENDENCY_V1", "obligation version")

    result = "următoarea măsurătoare începe la 20,2 grade înainte să atingă aerul"
    step1 = "dispozitivul păstrează diferența de 0,1 grade"
    step2 = "diferența pornește din afișarea de 20,1 grade la aceeași referință"
    factual = "După calibrare, dispozitivul a afișat 20,1 grade Celsius la aceeași referință."
    require(all(value in text for value in (result, step1, step2, factual)), "surface components")
    spans = {key: span(text, value) for key, value in (("result", result), ("step1", step1), ("step2", step2), ("factual", factual))}
    require(spans["result"]["character_coordinates"][0] < spans["step1"]["character_coordinates"][0]
            < spans["step2"]["character_coordinates"][0] < spans["factual"]["character_coordinates"][0], "reverse order")

    predicates = {
        "EXACT_AUTHORIZED_PROPOSITION_PRESERVED": True,
        "INVENTED_RESULT_PRESENTED_FIRST": True,
        "TWO_CANDIDATE_REVERSE_STEPS_PRESENT": True,
        "RESULT_DEPENDS_ON_IMMEDIATE_DIFFERENCE_STEP": True,
        "DIFFERENCE_STEP_RECOVERABLE_FROM_SELECTED_P3_RELATION": False,
        "EACH_STEP_NON_ARBITRARY": False,
        "COMPLETE_REVERSE_DEPENDENCY_CHAIN": False,
        "INVENTED_SEQUENCE_EXPLICITLY_NONFACTUAL": True,
        "FORBIDDEN_PERSONIFICATION_RECLASSIFICATION_AND_META_LANGUAGE_ABSENT": True,
    }
    failure = {
        "classification": "INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY",
        "earliest_failed_link": "STEP2_TO_SELECTED_FACTUAL_RELATION",
        "selected_proposition": "P3",
        "observed_gap": "The selected P3 relation supplies the 20.1-degree display and only 'the same reference'; it does not supply the reference's numeric value or another relation from which 0.1 is recoverable.",
        "why_arbitrary": "A different invented difference could replace 0.1 without contradicting or changing the selected P3 proposition.",
        "candidate_repair_performed": False,
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot05-g02c-conformance-receipt-v1", "schema_version": "1.0.0",
        "candidate_identity": g02["candidate_identity"], "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": g02["candidate_git_blob_oid_sha1"],
        "constructor_facing_packet_identity": packet["constructor_facing_packet_identity"],
        "obligation_instance_identity": obligation["obligation_instance_identity"],
        "obligation_version": obligation["obligation_version"], "selected_proposition_id": "P3",
        "surface_components": spans, "required_predicates": predicates, "failure": failure,
        "verdict": "FAIL_INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT05_G02C_CONFORMANCE_RECEIPT_V1", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot05-candidate-g02c-review-v1", "schema_version": "1.0.0",
        "candidate_identity": g02["candidate_identity"], "candidate_raw_sha256": g02["candidate_raw_sha256"],
        "creative_premise_family_id": g02["creative_premise_family_id"], "g02_commit": G02_COMMIT,
        "g02_receipt_identity": g02["g02_receipt_identity"], "conformance_receipt_identity": receipt_id,
        "predicate_verification": "FAIL_THREE_REQUIRED_DEPENDENCY_PREDICATES",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED", "sealed_mapping_accessed": False,
        "g03_performed": False, "candidate_modified": False,
        "g02c_verdict": "FAIL_INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY",
        "disposition": "G02C_REJECTED_STOP_NO_REPAIR",
        "eligibility": "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL",
        "authority_matrix": {key: False for key in ("g03_mechanism_recovery", "repair", "rewrite", "regeneration",
                                                     "owner_review", "training", "runtime_integration", "production_routing",
                                                     "g04b_pool_certification")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT05_G02C_REVIEW_V1", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": review["g02c_verdict"], "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"],
                      "next_action": "FREEZE_NONPOSITIVE_G02C_REJECTION_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
