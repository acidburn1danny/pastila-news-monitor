"""Freeze the factual-and-target-boundary review for Pilot 01 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INGESTION_COMMIT = "601ee4812d864301cb55620e3d239515163e9ef8"
EVIDENCE_COMMIT = "5c8f4226afd8c5ae4eede7b1fcb8e7ddee8ffec1"
SOURCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/source.utf8.txt"
ENVELOPE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/factual-authority-envelope.json"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-construction-attempt02-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-g02-v1.json"


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("G02 receipt already exists")
    source = git_bytes(INGESTION_COMMIT, SOURCE_PATH)
    envelope = json.loads(git_bytes(INGESTION_COMMIT, ENVELOPE_PATH))
    candidate = git_bytes(EVIDENCE_COMMIT, CANDIDATE_PATH)
    attempt = json.loads(git_bytes(EVIDENCE_COMMIT, ATTEMPT_PATH))
    assert hashlib.sha256(source).hexdigest() == envelope["source_sha256"]
    assert hashlib.sha256(candidate).hexdigest() == "2f848e2bc9d87b113df95996a4d49d48fbe4334d6c204ef707664158e23caf9d"
    assert attempt["candidate_identity"] == "f96e626487812b4a9ad32ef548d4ac715fae4ea9bb24590a73f942b0783f080f"
    assert attempt["creative_premise_family_id"] == "55f785b67f0d7f4103fc7c62bdc5826ee3bf3e7295cca6f8415f23e96decd1dc"
    text = candidate.decode("utf-8")
    source_text = source.decode("utf-8")
    p5 = next(p for p in envelope["propositions"] if p["proposition_id"] == "P5")
    p6 = next(p for p in envelope["propositions"] if p["proposition_id"] == "P6")
    p6_start, p6_end = p6["supporting_span"]["character_coordinates"]
    p6_surface = source_text[p6_start:p6_end]
    assert text.startswith(p6_surface + " ")
    assert "17:00" in text
    assert "explicit imaginară" in text and "strict fictivă" in text
    assert "fără pretenția că mobilierul muncește în realitate" in text
    core = {
        "schema_name": "batch2-development-pilot01-candidate-g02-v1",
        "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"],
        "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"],
        "candidate_git_blob_oid_sha1": "ae17e17b44dd6bef0bd0cee514c4ce20d4299725",
        "evidence_commit": EVIDENCE_COMMIT,
        "construction_evidence_identity": attempt["evidence_identity"],
        "creative_premise_family_id": attempt["creative_premise_family_id"],
        "partition": "DEVELOPMENT",
        "authority_binding": {
            "ingestion_commit": INGESTION_COMMIT,
            "source_sha256": envelope["source_sha256"],
            "source_commitment": envelope["source_commitment"],
            "factual_authority_envelope_identity": "7d0f1decc3e4908a03beedf4cec408cce096e07381b5e36f56c5e9dcb4975c65",
            "world_scope": envelope["world_scope"],
        },
        "g02_verdict": "PASS",
        "factual_assertion_trace": [
            {
                "candidate_assertion": "EXACT_P6_SUPPORTING_SPAN",
                "authority_proposition_ids": ["P6"],
                "trace_result": "EXACT_SOURCE_BOUND_ASSERTION_WITH_QUALIFICATION",
                "candidate_character_coordinates": [0, len(p6_surface)],
                "source_character_coordinates": [p6_start, p6_end],
                "source_utf8_byte_coordinates": p6["supporting_span"]["utf8_byte_coordinates"],
                "source_span_sha256": p6["supporting_span"]["span_sha256"],
            },
            {
                "candidate_assertion": "17:00_REFERENCE_INSIDE_EXPLICIT_FICTION",
                "authority_proposition_ids": ["P5"],
                "trace_result": "BOUND_TIME_REFERENCE_NONFACTUAL_USE_ONLY",
                "source_character_coordinates": p5["supporting_span"]["character_coordinates"],
                "source_utf8_byte_coordinates": p5["supporting_span"]["utf8_byte_coordinates"],
                "source_span_sha256": p5["supporting_span"]["span_sha256"],
            },
        ],
        "qualification_scope_result": "PASS_SYNTHETIC_UNIVERSE_QUALIFICATION_RETAINED_EXACTLY",
        "creative_nonfactual_separation_result": "PASS_EXPLICIT_IMAGINARY_AND_FICTITIOUS_MARKERS_WITH_REALITY_DISCLAIMER",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSAL_PREVALENCE_CHRONOLOGY_OR_STATUS_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_PROTECTED_OR_SENSITIVE_TARGET",
        "new_factual_premise_result": "PASS_NONE_THE_CONSEQUENCE_IS_EXPLICITLY_NONFACTUAL",
        "pragmatic_prohibited_conclusion_result": "PASS_REAL_WORLD_PERSONIFICATION_EXPRESSLY_DISCLAIMED",
        "post_construction_g02b_preserved": attempt["post_construction_g02b_verdict"] == "PASS",
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_BLIND_G03_DECISION",
        "authority_matrix": {key: False for key in (
            "g03_mechanism_recovery", "romanian_naturalness_review", "voice_review", "owner_review",
            "repair", "rewrite", "regeneration", "selection", "model_training", "runtime_integration",
            "production_routing")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT01_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
