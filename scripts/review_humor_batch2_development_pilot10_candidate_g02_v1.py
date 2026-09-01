"""Freeze Pilot 10 candidate 01's G02 factual-and-target-boundary review."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "3401c3e28b33498c290cb7506ef77778a7a415ff"
EVIDENCE_COMMIT = "d7d469ad3aaac777da506cafbf5ebd754890d76f"
COLLISION_COMMIT = "706593773da47989c1a83cb7c17291153d46a84c"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot10-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-construction-attempt01-v1.json"
COLLISION_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-fragment-collision-receipt-v5-2.json"
COLLISION_AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-fragment-collision-audit-v5-2.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02-v1.json"


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(not OUTPUT.exists(), "G02 receipt exists")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == COLLISION_COMMIT, "HEAD")
    source = git_bytes(INGESTION_COMMIT, PREFIX + "source.utf8.txt")
    envelope = json.loads(git_bytes(INGESTION_COMMIT, PREFIX + "factual-authority-envelope.json"))
    candidate = git_bytes(EVIDENCE_COMMIT, CANDIDATE_PATH)
    attempt = json.loads(git_bytes(EVIDENCE_COMMIT, ATTEMPT_PATH))
    collision = json.loads(git_bytes(COLLISION_COMMIT, COLLISION_RECEIPT_PATH))
    collision_audit = json.loads(git_bytes(COLLISION_COMMIT, COLLISION_AUDIT_PATH))

    require(hashlib.sha256(candidate).hexdigest() == "013c70e3c15833e789592915f5f31b62eeaed5c1148ff6b6f78607cb0c907464", "candidate hash")
    require(len(candidate) == 771, "candidate length")
    require(attempt["candidate_identity"] == "0f17fc88debe3ba4d91740cd7541a457aa7c63fdab86abd03e9944e6e85a8f89", "candidate identity")
    require(attempt["creative_premise_family_id"] == "fad53e912579f61a5e488e7448fe2050a10269d54bb2b41f510e2b63adf3e996", "creative family")
    require(attempt["creative_marker_family_id"] == "4005d38bf9fd6f6aeca7e109d1dccc39b0bc967fca93a33accc21d4349b8f842", "marker family")
    require(attempt["evidence_identity"] == "f74f47e30f75b48a35deaa395d3e3de17c1c7301bacd19afbdc8e334d066f8ba", "evidence")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    require(attempt["pre_emission_conformance"]["verdict"] == "PASS_PRE_EMISSION_REALIZATION_CONFORMANCE", "V5.2 conformance")
    require(collision["receipt_identity"] == "585b063e99a11289d4c430a552a56a0eab0663a82261236574ff2c8f7e04ce6c", "collision receipt")
    require(collision_audit["audit_identity"] == "adc5281062798e1f35ffa34596ee169afa9fb8f0294a26c618d7ae1760857690", "collision audit")
    require(collision["verdict"] == "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" and collision["collision_count"] == 0, "collision verdict")
    require(collision_audit["denyset_identity_and_seal"] == "PASS_EXACT_2135_HASHES", "denyset")
    require(collision["g02_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW", "G02 eligibility")

    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p3 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P3")
    start, end = p3["supporting_span"]["character_coordinates"]
    p3_surface = source_text[start:end]
    require(text.startswith(p3_surface), "exact P3 at candidate start")
    fiction = text[len(p3_surface):].rstrip("\n")
    require(fiction.startswith(" Într-un registru imaginar,"), "explicit imaginary scope")
    require("regula depozitului" in fiction and "zona devenită material horticol" in fiction, "fictional continuity")
    require(not any(term in text.casefold() for term in ("în realitate", "persoana a decis", "a intenționat",
                                                         "este vinovat", "este defect", "intervenție reală")), "unsupported assertion")

    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    require(candidate_oid == "8dfbc43c94190e5b0fca48d6bcd28adf55c21391", "candidate Git blob")
    require(candidate_oid == collision["candidate_git_blob_oid_sha1"], "collision candidate binding")
    traces = [
        {
            "candidate_assertion": "EXACT_P3_SUPPORTING_SPAN_AT_CANDIDATE_START",
            "authority_proposition_ids": ["P3"],
            "trace_result": "EXACT_SOURCE_BOUND_CONDITIONAL_APPROVAL_AND_STORAGE_DISPOSITION",
            "candidate_character_coordinates": [0, len(p3_surface)],
            "source_character_coordinates": [start, end],
            "source_utf8_byte_coordinates": p3["supporting_span"]["utf8_byte_coordinates"],
            "source_span_sha256": p3["supporting_span"]["span_sha256"],
            "modality": p3["modality"], "time": p3["time"], "scope": p3["scope"],
            "known_boundary": p3["known_boundary"], "unknown_boundary": p3["unknown_boundary"],
            "classification": "FACTUAL_AUTHORITY_EXACT",
        },
        {
            "candidate_assertion": "CONDITIONAL_APPROVAL_AND_MOVEMENT_RESTATED_INSIDE_IMAGINARY_SCOPE",
            "authority_proposition_ids": ["P3"],
            "trace_result": "COMPATIBLE_PARAPHRASE_RETAINS_BOTH_DOCUMENT_MATCH_CONDITIONS",
            "classification": "FACT_DERIVED_REFERENCE_WITHIN_EXPLICIT_NONFACTUAL_FRAME",
        },
        {
            "candidate_assertion": "STORAGE_ZONE_AND_APPROVED_LABEL_REFERENCES_INSIDE_IMAGINARY_CHAIN",
            "authority_proposition_ids": ["P3"],
            "trace_result": "SOURCE_OPERANDS_REUSED_WITHOUT_ASSERTING_NEW_REAL_WORLD_DISPOSITION",
            "classification": "FACT_DERIVED_OPERANDS_WITHIN_EXPLICIT_NONFACTUAL_FRAME",
        },
        {
            "candidate_assertion": "RULE_STORAGE_ZONE_TRANSFORMATION_AND_SELF_MOVING_DEPOT",
            "authority_proposition_ids": [],
            "trace_result": "EXPLICITLY_IMAGINARY_INVENTED_MATERIAL_OUTSIDE_FACTUAL_AUTHORITY",
            "classification": "CREATIVE_NONFACTUAL",
        },
    ]
    core = {
        "schema_name": "batch2-development-pilot10-candidate-g02-v1",
        "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"],
        "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"],
        "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT,
        "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"],
        "creative_marker_family_id": attempt["creative_marker_family_id"],
        "partition": "DEVELOPMENT",
        "fragment_collision_binding": {
            "commit": COLLISION_COMMIT, "verdict": collision["verdict"], "collision_count": collision["collision_count"],
            "receipt_identity": collision["receipt_identity"], "audit_identity": collision_audit["audit_identity"],
            "denyset_binding": collision_audit["denyset_identity_and_seal"],
        },
        "authority_binding": {
            "ingestion_commit": INGESTION_COMMIT, "source_sha256": envelope["source_sha256"],
            "source_commitment": envelope["source_commitment"],
            "factual_authority_envelope_identity": "fbae8cb29dcf203bae478b010fe19036239623551f22949b3cb56ac34ba18d21",
            "world_scope": envelope["world_scope"],
        },
        "g02_verdict": "PASS",
        "factual_assertion_trace": traces,
        "qualification_scope_result": "PASS_P3_BOTH_DOCUMENT_MATCH_CONDITIONS_TIME_SCOPE_AND_UNKNOWN_CRATE_QUALIFICATION_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_IMAGINARY_MARKER_SCOPES_ALL_INVENTED NODES_AND_TERMINAL_RESULT".replace(" ", "_"),
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_DEFECT_OR_OUTCOME_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_PERSON_PROTECTED_VULNERABLE_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_ALL_POST_P3_RULE_TRANSFORMATION_AND_TERMINAL_ACTIONS_REMAIN_EXPLICITLY_IMAGINARY",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_ACTUAL_MATCH_OCCURRENCE_UNSTATED_CRATE_STATUS_OR_REAL_WORLD_STORAGE_CONCLUSION",
        "romanian_naturalness_review_performed": False,
        "voice_review_performed": False,
        "post_construction_g02b_preserved": True,
        "pre_emission_conformance_preserved": True,
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in (
            "g02c_obligation_conformance", "g03_mechanism_recovery", "g03b", "g03c",
            "g04a_romanian_naturalness", "voice_review", "owner_review", "repair", "rewrite",
            "regeneration", "selection", "additional_construction", "g04b_pool_certification",
            "model_exposure", "training", "runtime_integration", "production_routing",
        )},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT10_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
