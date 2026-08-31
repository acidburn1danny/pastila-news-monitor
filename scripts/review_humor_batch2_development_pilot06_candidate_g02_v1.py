"""Freeze the G02 factual-and-target-boundary review for Pilot 06 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "46fe5cd153f1aec8acb8af7722123c2f9f0142c2"
EVIDENCE_COMMIT = "50966535cbcd4432b306a8929ad70fe1804330be"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot06-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot06-construction-attempt01-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-g02-v1.json"


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
    require(hashlib.sha256(candidate).hexdigest() == "e00b1b83507ece1808445a3f6cfd07286ee20eecc6f4208d9aa4940ab2fbc1a9", "candidate hash")
    require(len(candidate) == 302, "candidate length")
    require(attempt["candidate_identity"] == "61b4c89e4ec65ac211debc034ed35f47f79a2757551266a90fadf5acde270773", "candidate identity")
    require(attempt["creative_premise_family_id"] == "bc1ebc6a748fad7bcb3c8526b7568b5f30beefd15848db98aadc44f986c74994", "creative family")
    require(attempt["evidence_identity"] == "3a5ba3a2acd2c59b429d2f482c1011d30dec96bddce741fc4a6c72fcaab61a93", "evidence")
    require(attempt["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}, "attempt")
    require(attempt["post_construction_g02b_verdict"] == "PASS", "G02B")
    text, source_text = candidate.decode(), source.decode()
    p3 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P3")
    start, end = p3["supporting_span"]["character_coordinates"]
    p3_surface = source_text[start:end]
    factual_start = text.index(p3_surface)
    require(text[factual_start:].rstrip("\n") == p3_surface, "exact P3")
    fiction = text[:factual_start]
    require(fiction.startswith("Într-o continuare imaginară, "), "fiction marker")
    require("calendarul bibliotecii rămâne fără o zi" in fiction and "data a fost absorbită de registru" in fiction, "fictional sequence")
    require("deoarece apare lângă mențiunea „verificat”" in fiction, "fiction/fact bridge")
    require(not any(term in text for term in ("în realitate", "a intenționat", "a decis", "potrivit unei persoane")), "unsupported attribution")
    require("fotograf" not in text.casefold() and "arhiva de presă" not in text.casefold() and "următoarei inventarieri" not in text.casefold(), "unknown boundary")
    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    trace = {
        "candidate_assertion": "EXACT_P3_SUPPORTING_SPAN",
        "authority_proposition_ids": ["P3"],
        "trace_result": "EXACT_SOURCE_BOUND_ASSERTION_WITH_SESSION_QUALIFICATION_SYNTHETIC_SCOPE_AND_UNKNOWN_BOUNDARIES",
        "candidate_character_coordinates": [factual_start, factual_start + len(p3_surface)],
        "source_character_coordinates": [start, end],
        "source_utf8_byte_coordinates": p3["supporting_span"]["utf8_byte_coordinates"],
        "source_span_sha256": p3["supporting_span"]["span_sha256"],
        "modality": p3["modality"],
        "time": p3["time"],
        "scope": p3["scope"],
        "known_boundary": p3["known_boundary"],
        "unknown_boundary": p3["unknown_boundary"],
    }
    core = {
        "schema_name": "batch2-development-pilot06-candidate-g02-v1",
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
                              "factual_authority_envelope_identity": "847d37bb095d029758d1c8cce44e7685edf61016a151762f6ec7e12b7af2660c",
                              "world_scope": envelope["world_scope"]},
        "g02_verdict": "PASS",
        "factual_assertion_trace": [trace],
        "qualification_scope_result": "PASS_P3_SESSION_QUALIFICATION_SYNTHETIC_SCOPE_MODALITY_AND_UNKNOWN_BOUNDARIES_RETAINED",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_LOCAL_IMAGINARY_CONTINUATION_MARKER_COVERS_COMPLETE_CREATIVE_SEQUENCE",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE_VERIFIED_IS_EXACT_OWNER_AUTHORED_REGISTER_LABEL",
        "protected_target_result": "PASS_NO_REAL_PERSON_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_CALENDAR_AND_ABSORPTION_REMAIN_EXPLICITLY_IMAGINARY",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_REAL_WORLD_OR_UNSTATED_COLLECTION_FUTURE_OR_PERSON_CONCLUSION",
        "post_construction_g02b_preserved": True,
        "exposure_reconciliation_preserved": True,
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in ("g02c_obligation_conformance", "g03_mechanism_recovery", "owner_review", "repair", "rewrite", "regeneration", "selection", "model_training", "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT06_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid, "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
