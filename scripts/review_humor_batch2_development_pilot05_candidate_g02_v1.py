"""Freeze factual-and-target-boundary review for Pilot 05 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "585c986e0bd6b4717b3a1e90aad4aa5a7c8c0373"
EVIDENCE_COMMIT = "f04cce6cc83c9f489cc5c841653b4095367aa96e"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot05-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-construction-attempt01-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02-v1.json"


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
    require(not OUTPUT.exists(), "G02 receipt already exists")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == EVIDENCE_COMMIT,
            "HEAD differs from evidence commit")
    source = git_bytes(INGESTION_COMMIT, PREFIX + "source.utf8.txt")
    envelope = json.loads(git_bytes(INGESTION_COMMIT, PREFIX + "factual-authority-envelope.json"))
    candidate = git_bytes(EVIDENCE_COMMIT, CANDIDATE_PATH)
    attempt = json.loads(git_bytes(EVIDENCE_COMMIT, ATTEMPT_PATH))
    require(hashlib.sha256(source).hexdigest() == envelope["source_sha256"], "source/envelope")
    require(hashlib.sha256(candidate).hexdigest() == "8030222614461de66246eb9f2a14d1230e271b327007092f30f216f55a0d7166", "candidate hash")
    require(len(candidate) == 319, "candidate length")
    require(attempt["candidate_identity"] == "a7414fa9f1c50a5b674d9c3b5d7c531c46e6f8b70472893697a92d0309dc30ac", "candidate identity")
    require(attempt["creative_premise_family_id"] == "5a9ec724df58f6d855b298028c6c95aad4940b2379483971b1c51ce6b4ab22d7", "creative family")
    require(attempt["evidence_identity"] == "90e832ebd25773ed8b2a602724ea47bab3f557bc0231c22d117c8a6c02641c08", "evidence identity")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")

    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p3 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P3")
    start, end = p3["supporting_span"]["character_coordinates"]
    p3_surface = source_text[start:end]
    factual_start = text.index(p3_surface)
    require(text[factual_start:].rstrip("\n") == p3_surface, "exact terminal P3 assertion")
    fiction = text[:factual_start]
    require(fiction.startswith("Într-o continuare imaginară, "), "local fictional marking")
    require("următoarea măsurătoare începe la 20,2 grade înainte să atingă aerul" in fiction,
            "fictional initial disclosure")
    require("diferența de 0,1 grade" in fiction and "afișarea de 20,1 grade" in fiction,
            "fictional reverse disclosure")
    require(not any(term in text for term in ('"', "potrivit sursei", "în realitate", "a intenționat", "a decis")),
            "unsupported attribution")
    require("temperatura aerului exterior" not in text and "următoarei recalibrări" not in text,
            "prohibited unknown-boundary assertion")

    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    trace = {
        "candidate_assertion": "EXACT_P3_SUPPORTING_SPAN",
        "authority_proposition_ids": ["P3"],
        "trace_result": "EXACT_SOURCE_BOUND_ASSERTION_WITH_CALIBRATION_TIME_REFERENCE_AND_SYNTHETIC_SCOPE",
        "candidate_character_coordinates": [factual_start, factual_start + len(p3_surface)],
        "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p3["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p3["supporting_span"]["span_sha256"],
        "modality": p3["modality"], "time": p3["time"], "scope": p3["scope"],
        "known_boundary": p3["known_boundary"], "unknown_boundary": p3["unknown_boundary"],
    }
    core = {
        "schema_name": "batch2-development-pilot05-candidate-g02-v1", "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"], "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"], "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT, "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"], "partition": "DEVELOPMENT",
        "authority_binding": {"ingestion_commit": INGESTION_COMMIT, "source_sha256": envelope["source_sha256"],
                              "source_commitment": envelope["source_commitment"],
                              "factual_authority_envelope_identity": "d734ba6268619a67a41bcb9219f2d803d636f3507a95528c8ea0061a442bcebf",
                              "world_scope": envelope["world_scope"]},
        "g02_verdict": "PASS", "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P3_CALIBRATION_TIME_REFERENCE_SYNTHETIC_SCOPE_AND_UNKNOWN_BOUNDARY_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_IMAGINARY_CONTINUATION_MARKER_COVERS_COMPLETE_CREATIVE_SEQUENCE",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_CREATIVE_MEASUREMENT_AND_DIFFERENCE_REMAIN_EXPLICITLY_IMAGINARY",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_EXTERIOR_TEMPERATURE_FUTURE_RECALIBRATION_OR_REAL_WORLD_CONCLUSION",
        "post_construction_g02b_preserved": True, "exposure_reconciliation_preserved": True,
        "sealed_mapping_accessed": False, "mechanism_adjudication_performed": False,
        "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in ("g02c_obligation_conformance", "g03_mechanism_recovery",
                                                     "romanian_naturalness_review", "voice_review", "owner_review",
                                                     "repair", "rewrite", "regeneration", "selection", "model_training",
                                                     "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT05_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
