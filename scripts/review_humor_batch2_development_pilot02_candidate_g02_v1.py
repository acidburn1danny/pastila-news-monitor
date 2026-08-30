"""Freeze the factual-and-target-boundary review for Pilot 02 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "6220b9d86336ec6bd4a62a1cff528e96f973be2c"
EVIDENCE_COMMIT = "2662cf504509fdd8d37459810a28d9db6093de4b"
SOURCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/source.utf8.txt"
ENVELOPE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/factual-authority-envelope.json"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-construction-attempt01-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g02-v1.json"


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
    source = git_bytes(INGESTION_COMMIT, SOURCE_PATH)
    envelope = json.loads(git_bytes(INGESTION_COMMIT, ENVELOPE_PATH))
    candidate = git_bytes(EVIDENCE_COMMIT, CANDIDATE_PATH)
    attempt = json.loads(git_bytes(EVIDENCE_COMMIT, ATTEMPT_PATH))
    require(hashlib.sha256(source).hexdigest() == envelope["source_sha256"], "source/envelope binding")
    require(hashlib.sha256(candidate).hexdigest() == "5c50ca8e4ae5ea32301c02ec8ea4104482bbc9c8e3c7e8314516d09aeb591fd3", "candidate hash")
    require(attempt["candidate_identity"] == "4cc6bceef84e29d07e19d60dbbb1992b33fcb8af67373647f5fb8fedfce1d98c", "candidate identity")
    require(attempt["creative_premise_family_id"] == "ccb8ffaa1f8bd4f1cc40042854a76e73c3fb99d08f359da2e7ea952796bd7467", "creative family")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt state")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B state")

    text = candidate.decode("utf-8")
    source_text = source.decode("utf-8")
    p7 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P7")
    p7_start, p7_end = p7["supporting_span"]["character_coordinates"]
    p7_surface = source_text[p7_start:p7_end]
    require(text.startswith(p7_surface + " "), "exact P7 assertion not preserved")
    fiction = text[len(p7_surface) + 1:].rstrip("\n")
    require(fiction.startswith("Într-o continuare explicit fictivă, "), "fiction boundary marker")
    require("lipsa câștigătorului suspendă mai întâi încheierea testului" in fiction, "first fictional change")
    require("testul nu se mai poate încheia" in fiction and "încetează apoi să mai existe" in fiction,
            "dependent fictional continuation")
    require("în realitate" not in fiction.lower() and "potrivit sursei" not in fiction.lower(),
            "false factual attribution marker")

    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    trace = {
        "candidate_assertion": "EXACT_P7_SUPPORTING_SPAN",
        "authority_proposition_ids": ["P7"],
        "trace_result": "EXACT_SOURCE_BOUND_ASSERTION_WITH_TIME_SCOPE_AND_UNKNOWN_BOUNDARY",
        "candidate_character_coordinates": [0, len(p7_surface)],
        "source_character_coordinates": [p7_start, p7_end],
        "source_utf8_byte_coordinates": p7["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p7["supporting_span"]["span_sha256"],
        "modality": p7["modality"],
        "time": p7["time"],
        "scope": p7["scope"],
        "known_boundary": p7["known_boundary"],
        "unknown_boundary": p7["unknown_boundary"],
    }
    core = {
        "schema_name": "batch2-development-pilot02-candidate-g02-v1",
        "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"],
        "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"],
        "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT,
        "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"],
        "partition": "DEVELOPMENT",
        "authority_binding": {
            "ingestion_commit": INGESTION_COMMIT,
            "source_sha256": envelope["source_sha256"],
            "source_commitment": envelope["source_commitment"],
            "factual_authority_envelope_identity": "f3a66b5ccaa831acc171daa509700b16dbe2ebc9cfac30c8e68296e67c4bed9e",
            "world_scope": envelope["world_scope"],
        },
        "g02_verdict": "PASS",
        "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P7_MODALITY_TIME_SCOPE_AND_UNKNOWN_BOUNDARY_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_FICTION_MARKER_COVERS_COMPLETE_CONTINUATION",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_FICTIONAL_DEPENDENCY_REMAINS_OUTSIDE_AUTHORITY",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_REAL_WORLD_CONCLUSION_OR_UNMARKED_IMPLICATION",
        "post_construction_g02b_preserved": True,
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in (
            "g02c_obligation_conformance", "g03_mechanism_recovery", "romanian_naturalness_review",
            "voice_review", "owner_review", "repair", "rewrite", "regeneration", "selection",
            "model_training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"],
                      "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
