"""Freeze factual-and-target-boundary review for Pilot 04 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "4e4afc730be7600fb0b6ce8abf822bce868b0565"
EVIDENCE_COMMIT = "f966fd48dd831fea592963bf8b7b04f5df9ff559"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot04-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-construction-attempt01-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-g02-v1.json"


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
    require(hashlib.sha256(candidate).hexdigest() == "e231a549685103da5c6e0e4f9b9e93459d86e7c7ae0247ad11f15d55a3426b0b", "candidate hash")
    require(attempt["candidate_identity"] == "cf34033fb7017ff29146524108d4cb3fcbf8229681d054d2085dbaba294436e1", "candidate identity")
    require(attempt["creative_premise_family_id"] == "726eb45203c35592ea2781ac778b7147fd97794d907f0973861acbfa1e3bc6fc", "creative family")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p5 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    start, end = p5["supporting_span"]["character_coordinates"]
    p5_surface = source_text[start:end]
    require(text.startswith(p5_surface + " "), "exact P5 assertion")
    fiction = text[len(p5_surface) + 1:].rstrip("\n")
    require(fiction.startswith("În povestea expoziției, "), "local fictional marking")
    require("un participant cu o astfel de acreditare rămâne mai întâi în afara zonei B" in fiction,
            "first fictional situation")
    require("neputând ajunge la demonstrație" in fiction and "cât de bine funcționează interdicția" in fiction,
            "dependent fictional situation")
    require(not any(term in fiction for term in ('"', "potrivit sursei", "în realitate", "a intenționat", "a decis")), "unsupported attribution")
    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    trace = {
        "candidate_assertion": "EXACT_P5_SUPPORTING_SPAN", "authority_proposition_ids": ["P5"],
        "trace_result": "EXACT_SOURCE_BOUND_ASSERTION_WITH_TIME_SCOPE_AND_UNKNOWN_BOUNDARY",
        "candidate_character_coordinates": [0, len(p5_surface)], "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p5["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p5["supporting_span"]["span_sha256"], "modality": p5["modality"],
        "time": p5["time"], "scope": p5["scope"], "known_boundary": p5["known_boundary"],
        "unknown_boundary": p5["unknown_boundary"],
    }
    core = {
        "schema_name": "batch2-development-pilot04-candidate-g02-v1", "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"], "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"], "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT, "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"], "partition": "DEVELOPMENT",
        "authority_binding": {"ingestion_commit": INGESTION_COMMIT, "source_sha256": envelope["source_sha256"],
                              "source_commitment": envelope["source_commitment"],
                              "factual_authority_envelope_identity": "40c92efd6ee0ae4b99d422094d2d28073ad8602df0c1528a38bbf681aba3de8d",
                              "world_scope": envelope["world_scope"]},
        "g02_verdict": "PASS", "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P5_MODALITY_TIME_SCOPE_AND_UNKNOWN_BOUNDARY_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_STORY_MARKER_COVERS_COMPLETE_CONTINUATION",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_FICTIONAL_DEPENDENCY_REMAINS_OUTSIDE_AUTHORITY",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_REAL_WORLD_CONCLUSION_OR_UNMARKED_IMPLICATION",
        "post_construction_g02b_preserved": True, "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False, "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in ("g02c_obligation_conformance", "g03_mechanism_recovery",
                                                     "romanian_naturalness_review", "voice_review", "owner_review",
                                                     "repair", "rewrite", "regeneration", "selection", "model_training",
                                                     "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
