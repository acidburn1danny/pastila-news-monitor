"""Freeze Pilot 13 candidate 01's independent G02 boundary review."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
INGESTION_COMMIT = "34a39ae37563d923f55549fb620601a46e4f9d63"
EVIDENCE_COMMIT = "6a874a1d62dd184c4c972ef23445a6935bb17da8"
COLLISION_COMMIT = "b1fa1a50e9a50dbb70d3e54c8aca359d4c024a5e"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot13-ingestion-v1/"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-v1.txt"
ATTEMPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-construction-attempt01-v1.json"
COLLISION_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-fragment-collision-receipt-v5-3-3.json"
COLLISION_AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-fragment-collision-audit-v5-3-3.json"
OUTPUT = ART / "humor-mechanics-batch2-development-pilot13-candidate01-g02-v1.json"


def git_bytes(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value, message):
    if not value:
        raise SystemExit(message)


def main():
    require(not OUTPUT.exists(), "G02 receipt exists")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", COLLISION_COMMIT, "HEAD"], cwd=ROOT).returncode == 0, "collision commit")
    source = git_bytes(INGESTION_COMMIT, PREFIX + "source.utf8.txt")
    envelope = json.loads(git_bytes(INGESTION_COMMIT, PREFIX + "factual-authority-envelope.json"))
    candidate = git_bytes(EVIDENCE_COMMIT, CANDIDATE_PATH)
    attempt = json.loads(git_bytes(EVIDENCE_COMMIT, ATTEMPT_PATH))
    collision = json.loads(git_bytes(COLLISION_COMMIT, COLLISION_RECEIPT_PATH))
    collision_audit = json.loads(git_bytes(COLLISION_COMMIT, COLLISION_AUDIT_PATH))
    require(hashlib.sha256(candidate).hexdigest() == "907392cd76554340b09ef27145256b45f3c1ae013f41f4e4503ea156dc546759", "candidate hash")
    require(len(candidate) == 552 and attempt["candidate_identity"] == "00dfb416e99d9d489c05cbf317a8b9654d51a5ecb0994220032c0cd68efe2fb6", "candidate binding")
    require(attempt["evidence_identity"] == "a53ee85f94b7d30570ac77dac1f0345aaf642eea98383fe7b2bac89ca29fcd9e", "evidence")
    require(attempt["pre_emission_v5_3_3_conformance"]["verdict"] == "PASS_ACTUAL_SURFACE_SEMANTIC_CONFORMANCE", "provenance conformance")
    require(collision["receipt_identity"] == "983a9dda4fa2bab8c72324f6b7e52a02c958d11ca7de01fe26e2bad3e7d0d9b2", "collision receipt")
    require(collision_audit["audit_identity"] == "9137c2d2937691f97c19a5529525c6bc485dc01118d617cfc9a9e69e53cc7eed", "collision audit")
    require(collision["verdict"] == "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" and collision["collision_count"] == 0, "collision verdict")
    require(collision["g02_eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW", "eligibility")

    text, source_text = candidate.decode("utf-8"), source.decode("utf-8")
    p5 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    start, end = p5["supporting_span"]["character_coordinates"]
    p5_surface = source_text[start:end]
    factual_clause = p5_surface.rstrip(".\n")
    fact_start = text.casefold().index(factual_clause.casefold())
    fact_end = fact_start + len(factual_clause)
    require(text[fact_start:fact_end].casefold() == factual_clause.casefold(), "P5 factual trace")
    require(text.startswith("În mica ficțiune,"), "fiction marker")
    require(all(term in text for term in ("după montare", "poziția efectivă a fiecărui senzor", "ora instalării", "jurnalul campaniei")), "P5 operands")
    require(not any(term in text.casefold() for term in ("în realitate", "a intenționat", "este vinovat",
                                                         "este defect", "intervenție reală", "citat:")), "unsupported assertion")
    candidate_oid = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    require(candidate_oid == "9a643cff281455ee0b4c9772f9740175ab27753b", "candidate blob")
    require(candidate_oid == collision["candidate_git_blob_oid_sha1"], "collision binding")
    traces = [
        {"candidate_assertion": "P5_POST_INSTALLATION_SENSOR_POSITION_AND_INSTALLATION_TIME_RECORDED_IN_CAMPAIGN_LOG",
         "authority_proposition_ids": ["P5"], "trace_result": "PASS_EXACT_LEXICAL_FACTUAL_CLAUSE_EMBEDDED_WITHOUT_TERMINAL_PUNCTUATION",
         "candidate_character_coordinates": [fact_start, fact_end], "source_character_coordinates": [start, end],
         "source_utf8_byte_coordinates": p5["supporting_span"]["utf8_byte_coordinates"],
         "source_span_sha256": p5["supporting_span"]["span_sha256"], "modality": p5["modality"],
         "time": p5["time"], "scope": p5["scope"], "known_boundary": p5["known_boundary"],
         "unknown_boundary": p5["unknown_boundary"], "classification": "FACTUAL_AUTHORITY_P5"},
        {"candidate_assertion": "LOCAL_RECORDING_ELIGIBILITY_AND_LOG_BOUND_STATE_CHAIN",
         "authority_proposition_ids": [], "trace_result": "EXPLICITLY_SCOPED_BY_INITIAL_FICTION_MARKER",
         "classification": "CREATIVE_NONFACTUAL"},
        {"candidate_assertion": "LOG_REQUIRES_SENSOR_TIMESHEETS_FOR_OCCUPIED_CENTIMETERS",
         "authority_proposition_ids": [], "trace_result": "EXPLICITLY_FICTIONAL_TERMINAL_RESULT_NOT_REAL_WORLD_CLAIM",
         "classification": "CREATIVE_NONFACTUAL"},
    ]
    core = {
        "schema_name": "batch2-development-pilot13-candidate-g02-v1", "schema_version": "1.0.0",
        "candidate_identity": attempt["candidate_identity"], "candidate_raw_sha256": attempt["candidate_surface_sha256"],
        "candidate_byte_length": attempt["candidate_surface_byte_length"], "candidate_git_blob_oid_sha1": candidate_oid,
        "evidence_commit": EVIDENCE_COMMIT, "construction_evidence_identity": attempt["evidence_identity"],
        "partition": "DEVELOPMENT", "selected_proposition_id": "P5", "p6_fallback_authority": "ABSENT",
        "fragment_collision_binding": {"commit": COLLISION_COMMIT, "verdict": collision["verdict"],
            "collision_count": collision["collision_count"], "receipt_identity": collision["receipt_identity"],
            "audit_identity": collision_audit["audit_identity"], "denyset_binding": collision_audit["denyset_identity_and_seal"]},
        "authority_binding": {"ingestion_commit": INGESTION_COMMIT, "source_sha256": envelope["source_sha256"],
            "source_commitment": envelope["source_commitment"], "world_scope": envelope["world_scope"],
            "selected_supporting_span_sha256": p5["supporting_span"]["span_sha256"]},
        "g02_verdict": "PASS", "factual_assertion_trace": traces,
        "qualification_result": "PASS_POST_INSTALLATION_QUALIFICATION_RETAINED",
        "modality_result": "PASS_ASSERTED_SOURCE_FACT_RETAINED_WITHOUT_STRENGTHENING",
        "temporal_boundary_result": "PASS_AFTER_INSTALLATION_RETAINED",
        "scope_boundary_result": "PASS_OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "known_unknown_boundary_result": "PASS_ACTUAL_POSITION_AND_INSTALLATION_TIME_LOGGING_ONLY_NO_UNSTATED_REAL_LOG_CONTENT",
        "creative_nonfactual_separation_result": "PASS_INITIAL_EXPLICIT_FICTION_MARKER_SCOPES_ALL_INVENTED_LINKS_AND_TERMINAL_RESULT",
        "unsupported_premise_result": "PASS_NONE_OUTSIDE_EXPLICIT_FICTION",
        "unsupported_inference_result": "PASS_NO_REAL_WORLD_INTENT_MOTIVE_PRIVATE_STATE_CAUSALITY_PREVALENCE_CHRONOLOGY_DEFECT_OR_OUTCOME_ASSERTION",
        "invented_quotation_or_private_knowledge_result": "PASS_NONE",
        "protected_target_result": "PASS_NO_PERSON_PROTECTED_VULNERABLE_OR_SENSITIVE_TARGET",
        "pragmatic_prohibited_conclusion_result": "PASS_NO_REAL_SENSOR_AGENCY_LOG_DEMAND_OR_ADDITIONAL_CAMPAIGN_OUTCOME_ASSERTED",
        "factual_authority_widening": "ABSENT_EXACT_P5_ONLY", "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False, "candidate_bytes_unchanged": True,
        "construction_conformance_treated_as_provenance_only": True, "g02c_obligation_conformance_performed": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE",
        "authority_matrix": {key: False for key in ("g02c_obligation_conformance", "g03_mechanism_recovery",
            "g03b", "g03c", "romanian_naturalness", "voice_review", "owner_review", "repair", "rewrite",
            "regeneration", "selection", "additional_construction", "g04b_pool_certification", "model_exposure",
            "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "g02_receipt_identity": seal("B2_DEVELOPMENT_PILOT13_CANDIDATE_G02_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02_verdict": receipt["g02_verdict"], "g02_receipt_identity": receipt["g02_receipt_identity"],
                      "candidate_git_blob_oid_sha1": candidate_oid,
                      "next_gate": "G02C_OBLIGATION_CONFORMANCE_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
