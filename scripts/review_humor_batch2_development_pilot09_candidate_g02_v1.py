"""Freeze the G02 factual-and-target-boundary review for Pilot 09 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "8991524fb136d29daa5f559ba8d9aef7386a2ac8"
EVIDENCE_COMMIT = "6b39e6b2dc83662ad432235889b058d3a6b096aa"
COLLISION_COMMIT = "c06404215272d60549c09725915486c155fda0a4"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-construction-attempt01-v1.json"
COLLISION_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-fragment-collision-receipt-v5-1.json"
COLLISION_AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-fragment-collision-audit-v5-1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02-v1.json"


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

    require(hashlib.sha256(candidate).hexdigest() == "3249775af5b93a68f00ab1e8217652a1411db03d61a40dfbe1e1fa3f7cd7e307", "candidate hash")
    require(len(candidate) == 246, "candidate length")
    require(attempt["candidate_identity"] == "57fd9aa630aee874230759b83ee4cd11eaf99254cde43acf1b11e139824a58e1", "candidate identity")
    require(attempt["creative_premise_family_id"] == "b8271e5f4ac1facea81e8b6ebb5f8048fcc43353b777e478ea0626a9eb196a08", "creative family")
    require(attempt["evidence_identity"] == "bc62a11a24443114113e0f109cd37f9b534980186f052d0dcb3757305eef9c61", "evidence")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    require(collision["receipt_identity"] == "a2e0314bf023f416244645e8a79583ddae71a5007beeecbf29aba5dbdd480c76", "collision receipt")
    require(collision_audit["audit_identity"] == "50b754b4b8666af6dd1eb98bba23d6ad28011acb03f2212b79cd81487d1a1ed3", "collision audit")
    require(collision["verdict"] == "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" and collision["collision_count"] == 0, "collision verdict")
    require(collision_audit["denyset_identity_and_seal"] == "PASS_EXACT_1952_HASHES", "denyset")
    require(collision["g02_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW", "G02 eligibility")

    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p5 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    start, end = p5["supporting_span"]["character_coordinates"]
    p5_surface = source_text[start:end]
    require(text.startswith(p5_surface), "exact P5 at candidate start")
    fiction = text[len(p5_surface):].rstrip("\n")
    require(fiction == " Într-un cadru explicit imaginar, relația continuă prin două consecințe locale, iar ultima depinde de întregul traseu inventat.", "exact marked nonfactual continuation")
    require(not any(term in text.casefold() for term in ("în realitate", "a intenționat", "a decis", "este defect", "intervenție reală")), "unsupported assertion")

    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    require(candidate_oid == "fd1c7c024523faf63efe610849620364638a48b3", "candidate Git blob")
    require(candidate_oid == collision["candidate_git_blob_oid_sha1"], "collision candidate binding")
    trace = {
        "candidate_assertion": "EXACT_P5_SUPPORTING_SPAN_AT_CANDIDATE_START",
        "authority_proposition_ids": ["P5"],
        "trace_result": "EXACT_SOURCE_BOUND_CONDITIONAL_AUTOMATIC_NONSTART_ASSERTION_WITH_NONOCCURRENCE_AND_COMPONENT_DEFECT_UNKNOWNS_RETAINED",
        "candidate_character_coordinates": [0, len(p5_surface)],
        "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p5["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p5["supporting_span"]["span_sha256"],
        "modality": p5["modality"],
        "time": p5["time"],
        "scope": p5["scope"],
        "known_boundary": p5["known_boundary"],
        "unknown_boundary": p5["unknown_boundary"],
        "post_span_classification": "EXPLICITLY_MARKED_IMAGINARY_RELATIONAL_CONTINUATION_NOT_FACTUAL_AUTHORITY",
    }
    core = {
        "schema_name": "batch2-development-pilot09-candidate-g02-v1",
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
            "commit": COLLISION_COMMIT,
            "verdict": collision["verdict"],
            "collision_count": collision["collision_count"],
            "receipt_identity": collision["receipt_identity"],
            "audit_identity": collision_audit["audit_identity"],
            "denyset_binding": collision_audit["denyset_identity_and_seal"],
        },
        "authority_binding": {
            "ingestion_commit": INGESTION_COMMIT,
            "source_sha256": envelope["source_sha256"],
            "source_commitment": envelope["source_commitment"],
            "factual_authority_envelope_identity": "9e791c37ce2fca9b927e3c386ede1ae0c2c0019e1301261e5bb900c7ffaa39f9",
            "world_scope": envelope["world_scope"],
        },
        "g02_verdict": "PASS",
        "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P5_DISJUNCTIVE_CONDITION_AUTOMATIC_NONSTART_SYNTHETIC_SCOPE_AND_UNKNOWN_OCCURRENCE_COMPONENT_DEFECT_BOUNDARIES_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_IMAGINARY_MARKER_SCOPES_COMPLETE_POST_P5_CONTINUATION",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_INTERVENTION_OR_COMPONENT_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_POST_P5_LANGUAGE_DESCRIBES_ONLY_EXPLICITLY_IMAGINARY_RELATIONAL_STRUCTURE",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_ACTUAL_CONDITION_OCCURRENCE_DEFECTIVE_COMPONENT_INTERVENTION_OR_REAL_WORLD_OUTCOME_CONCLUSION",
        "romanian_naturalness_review_performed": False,
        "voice_review_performed": False,
        "post_construction_g02b_preserved": True,
        "exposure_reconciliation_preserved": True,
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in (
            "g02c_obligation_conformance", "g03_mechanism_recovery", "g04a_romanian_naturalness",
            "voice_review", "owner_review", "repair", "rewrite", "regeneration", "selection",
            "model_training", "runtime_integration", "production_routing", "g04b_pool_certification",
        )},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT09_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
