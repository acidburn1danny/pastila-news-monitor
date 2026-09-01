"""Freeze the G02 factual-and-target-boundary review for Pilot 07 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "914f9041247783f00220025d3d940089abc0fd73"
EVIDENCE_COMMIT = "b88e13df272ff79a2d39d22b05b6d962f3785713"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot07-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-construction-attempt01-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g02-v1.json"


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
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == EVIDENCE_COMMIT, "HEAD")
    source = git_bytes(INGESTION_COMMIT, PREFIX + "source.utf8.txt")
    envelope = json.loads(git_bytes(INGESTION_COMMIT, PREFIX + "factual-authority-envelope.json"))
    candidate = git_bytes(EVIDENCE_COMMIT, CANDIDATE_PATH)
    attempt = json.loads(git_bytes(EVIDENCE_COMMIT, ATTEMPT_PATH))
    require(hashlib.sha256(candidate).hexdigest() == "769228fc99006e0f665360f28805f31d4480419095de1f1fba5794319cc1bfa8", "candidate hash")
    require(len(candidate) == 366, "candidate length")
    require(attempt["candidate_identity"] == "44c76c090e226d0ef947e2fc07307fb862761e94950c4eb378b8b3d258427bc1", "candidate identity")
    require(attempt["creative_premise_family_id"] == "39db5384af4870785ef54b076c73afed4be48a82fedd5a899f576f97d0dac558", "creative family")
    require(attempt["evidence_identity"] == "29a2335640adfc33ba2c173b4256582687eb2e4993c53722c20c46d281f96f19", "evidence")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    text, source_text = candidate.decode(), source.decode()
    p5 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    start, end = p5["supporting_span"]["character_coordinates"]
    p5_surface = source_text[start:end]
    factual_start = text.index(p5_surface)
    require(factual_start == 0 and text.startswith(p5_surface), "exact P5")
    fiction = text[len(p5_surface):].rstrip("\n")
    require(fiction.startswith(" Într-o continuare imaginară, "), "fiction marker")
    require("înscrierea adaugă raportului o rubrică nouă" in fiction, "fictional link one")
    require("analiza ei cere o nouă înscriere" in fiction and "ciclul se repetă" in fiction, "fictional links two and three")
    require("intervenție" not in fiction.casefold() and "tehnician" not in fiction.casefold(), "unknown intervention boundary")
    require(not any(term in text.casefold() for term in ("în realitate", "a intenționat", "a decis", "potrivit unei persoane")), "unsupported attribution")
    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    trace = {
        "candidate_assertion": "EXACT_P5_SUPPORTING_SPAN",
        "authority_proposition_ids": ["P5"],
        "trace_result": "EXACT_SOURCE_BOUND_CONDITIONAL_ASSERTION_WITH_REPORT_ANALYSIS_PURPOSE_AND_UNKNOWN_INTERVENTION_BOUNDARY",
        "candidate_character_coordinates": [factual_start, factual_start + len(p5_surface)],
        "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p5["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p5["supporting_span"]["span_sha256"],
        "modality": p5["modality"],
        "time": p5["time"],
        "scope": p5["scope"],
        "known_boundary": p5["known_boundary"],
        "unknown_boundary": p5["unknown_boundary"],
    }
    core = {
        "schema_name": "batch2-development-pilot07-candidate-g02-v1",
        "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"],
        "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"],
        "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT,
        "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"],
        "partition": "DEVELOPMENT",
        "authority_binding": {"ingestion_commit": INGESTION_COMMIT, "source_sha256": envelope["source_sha256"],
                              "source_commitment": envelope["source_commitment"],
                              "factual_authority_envelope_identity": "25f9ec7a698ce3e2060642f10f59cf511c29130f29b403066bb3e965c866f6d4",
                              "world_scope": envelope["world_scope"]},
        "g02_verdict": "PASS",
        "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P5_CONDITIONAL_OBSERVATION_REPORT_ANALYSIS_QUALIFICATION_SYNTHETIC_SCOPE_AND_UNKNOWN_INTERVENTION_BOUNDARY_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_IMAGINARY_CONTINUATION_MARKER_COVERS_COMPLETE_CREATIVE_SEQUENCE",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_REPORT_RUBRIC_CYCLE_REMAINS_EXPLICITLY_IMAGINARY",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_REAL_WORLD_PROBLEM_INTERVENTION_OR_PERSON_CONCLUSION",
        "post_construction_g02b_preserved": True,
        "exposure_reconciliation_preserved": True,
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in ("g02c_obligation_conformance", "g03_mechanism_recovery", "owner_review", "repair", "rewrite", "regeneration", "selection", "model_training", "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid, "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
