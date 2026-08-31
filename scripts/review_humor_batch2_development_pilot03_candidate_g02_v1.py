"""Freeze factual-and-target-boundary review for Pilot 03 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "8aaeccbbca9d45fb9d522505f82d173e1090b3b6"
EVIDENCE_COMMIT = "aaec1abbf7e538a8a1f8a628677360695298c03e"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot03-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-construction-attempt01-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-g02-v1.json"


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
    require(hashlib.sha256(candidate).hexdigest() == "86f058253be11227bf40a0de4842bf79ae7458b2a89f11c8fca033477e0a626d", "candidate hash")
    require(attempt["candidate_identity"] == "b4555cc43bf16a466734aed46e93baa83bd9bc37d52d3826976be3370ccef72d", "candidate identity")
    require(attempt["creative_premise_family_id"] == "dd530bad539b8ce3e40d4a4b35eacb75a040e84ad44b051652c6266519b88bcf", "creative family")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p7 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P7")
    start, end = p7["supporting_span"]["character_coordinates"]
    p7_surface = source_text[start:end]
    require(text.startswith(p7_surface + " "), "exact P7 assertion")
    fiction = text[len(p7_surface) + 1:].rstrip("\n")
    require(fiction.startswith("În povestea imaginară a coletului, "), "local fictional marking")
    require("necunoașterea conținutului lasă lista de inventar goală" in fiction, "first fictional situation")
    require("lista goală nu poate confirma nimic" in fiction and "singurul lucru care mai poate fi inventariat" in fiction,
            "dependent fictional situation")
    require(not any(term in fiction for term in ('"', "potrivit sursei", "în realitate", "a intenționat", "a decis")), "unsupported attribution")
    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    trace = {
        "candidate_assertion": "EXACT_P7_SUPPORTING_SPAN", "authority_proposition_ids": ["P7"],
        "trace_result": "EXACT_SOURCE_BOUND_ASSERTION_WITH_TIME_SCOPE_AND_UNKNOWN_BOUNDARY",
        "candidate_character_coordinates": [0, len(p7_surface)], "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p7["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p7["supporting_span"]["span_sha256"], "modality": p7["modality"],
        "time": p7["time"], "scope": p7["scope"], "known_boundary": p7["known_boundary"],
        "unknown_boundary": p7["unknown_boundary"],
    }
    core = {
        "schema_name": "batch2-development-pilot03-candidate-g02-v1", "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"], "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"], "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT, "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"], "partition": "DEVELOPMENT",
        "authority_binding": {"ingestion_commit": INGESTION_COMMIT, "source_sha256": envelope["source_sha256"],
                              "source_commitment": envelope["source_commitment"],
                              "factual_authority_envelope_identity": "3808b24094412383f4a152233c7f18d098ea4cfa6a90c2a41ee1093c8ac02ac3",
                              "world_scope": envelope["world_scope"]},
        "g02_verdict": "PASS", "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P7_MODALITY_TIME_SCOPE_AND_UNKNOWN_BOUNDARY_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_IMAGINARY_STORY_MARKER_COVERS_COMPLETE_CONTINUATION",
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
                                                     "runtime_integration", "production_routing")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
