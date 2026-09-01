"""Freeze the G02 factual-and-target-boundary review for Pilot 08 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "784eaacbc12c574e9a4d16e9f0059ae60a32b396"
EVIDENCE_COMMIT = "d05643f2da3280a0bd88a5fe018c61c913186526"
COLLISION_COMMIT = "25ec47cf225cf991c7ae6693401894bd317003b2"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot08-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-construction-attempt01-v1.json"
COLLISION_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-fragment-collision-receipt-v4.json"
COLLISION_AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-fragment-collision-audit-v4.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02-v1.json"


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

    require(hashlib.sha256(candidate).hexdigest() == "bc71da32026e9173440a494279fd4dca752cfc8c5547abcaa1ad922bdda0368a", "candidate hash")
    require(len(candidate) == 603, "candidate length")
    require(attempt["candidate_identity"] == "6f2aca6eafc4773576a00001d83d1a0e5c2bf5a2c53d1ae2930c2f3147457fb8", "candidate identity")
    require(attempt["creative_premise_family_id"] == "d74623b0e85e24d1128523c00d85f03ccd4495c78f335ca92268369d4039777e", "creative family")
    require(attempt["creative_marker_family_id"] == "758cbce681ac51bbf1608018e69b63cf132fafcb795d9527234c0e25665c108b", "creative marker family")
    require(attempt["evidence_identity"] == "657a8ca2fb8023b9a34d51b0958c5cde9c9190f458b84da74c91a4895e56df88", "evidence")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    require(collision["receipt_identity"] == "a2645ddfb3357f9a8ebd55c1e661db1197bf0e41bf4fe945c2b168c4ec16c89e", "collision receipt")
    require(collision_audit["audit_identity"] == "b05990a388ee7a29d91511315e38fcb2959ae3736a2d5753d501b87218742c2a", "collision audit")
    require(collision["verdict"] == "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" and collision["collision_count"] == 0, "collision verdict")
    require(collision_audit["denyset_identity_and_seal"] == "PASS_EXACT_1617_HASHES", "denyset")
    require(collision["g02_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW", "G02 eligibility")

    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p5 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    start, end = p5["supporting_span"]["character_coordinates"]
    p5_surface = source_text[start:end]
    require(text.startswith(p5_surface), "exact P5 at candidate start")
    fiction = text[len(p5_surface):].rstrip("\n")
    require(fiction.startswith(" În variantă inventată a regulăii, "), "explicit invented-variant marker")
    require("mută controlul înapoi spre" in fiction, "creative link one")
    require("regulăa se aplică din nou" in fiction, "creative link two")
    require("controlul ajunge să verifice chiar regulăa" in fiction, "creative link three")
    require(not any(term in text.casefold() for term in ("în realitate", "a intenționat", "a decis", "potrivit unei persoane")), "unsupported attribution")

    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    require(candidate_oid == collision["candidate_git_blob_oid_sha1"], "candidate Git blob")
    trace = {
        "candidate_assertion": "EXACT_P5_SUPPORTING_SPAN_AT_CANDIDATE_START",
        "authority_proposition_ids": ["P5"],
        "trace_result": "EXACT_SOURCE_BOUND_CONDITIONAL_RECORDING_AND_LATER_CHECK_ASSERTION_WITH_UNKNOWN_FAILURE_AND_COMPONENT_OUTCOME_BOUNDARIES",
        "candidate_character_coordinates": [0, len(p5_surface)],
        "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p5["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p5["supporting_span"]["span_sha256"],
        "modality": p5["modality"],
        "time": p5["time"],
        "scope": p5["scope"],
        "known_boundary": p5["known_boundary"],
        "unknown_boundary": p5["unknown_boundary"],
        "post_span_classification": "EXPLICITLY_MARKED_INVENTED_VARIANT_NOT_FACTUAL_AUTHORITY",
    }
    core = {
        "schema_name": "batch2-development-pilot08-candidate-g02-v1",
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
            "factual_authority_envelope_identity": "9988272b9a99ca29fbd706abc4b6f57bbb6c87a62bf2fe4a79de0919a4051847",
            "world_scope": envelope["world_scope"],
        },
        "g02_verdict": "PASS",
        "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P5_CONDITIONAL_TRIGGER_SYNTHETIC_SCOPE_AND_UNKNOWN_ZONE_FAILURE_COMPONENT_DEFECT_OUTCOMES_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_INVENTED_VARIANT_MARKER_SCOPES_COMPLETE_POST_P5_RECURSIVE_RULE_CONTROL_SEQUENCE",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_COMPONENT_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_REPEATED_P5_TERMS_AND_RECURSIVE_RULE_CONTROL_SEQUENCE_REMAIN_EXPLICITLY_INVENTED",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_ACTUAL_ZONE_FAILURE_DEFECTIVE_COMPONENT_OR_REAL_WORLD_CONCLUSION",
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
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT08_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "g02_verdict": receipt["g02_verdict"],
        "g02_receipt_identity": receipt["g02_receipt_identity"],
        "candidate_git_blob_oid_sha1": candidate_oid,
        "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
