"""Freeze Pilot 06 as non-positive ambiguous/confusable DEVELOPMENT evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "49bebda98e6bc44fe1fc5a48f3401db8f0d3e96c"
ART = ROOT / "docs/artifacts"
OUTPUT = ART / "humor-mechanics-batch2-development-pilot06-candidate01-disposition-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("disposition exists")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    open_pass = load("docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-open-blind-pass-v1.json")
    contrast = load("docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-contrast-blind-pass-v1.json")
    reconciliation = load("docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-reconciliation-v1.json")
    g03 = load("docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-receipt-v1.json")
    if g03["g03_validity"] != "VALID_BLIND_REVIEW" or g03["g03_receipt_identity"] != "8b4bf0afeacf6875681106e722bcb56c3997e4a402d0f04ba69c5d7e8dbcbb55":
        raise SystemExit("G03")
    if reconciliation["reconciliation_identity"] != "778c28a69caaccf4cc75d8c6261a9075ba6b3c1f905e68a57758b9be1be92958":
        raise SystemExit("reconciliation")
    if reconciliation["reconciliation_classification"] != "AMBIGUOUS_MECHANISM":
        raise SystemExit("classification")
    core = {
        "schema_name": "batch2-development-pilot06-ambiguous-disposition-v1", "schema_version": "1.0.0",
        "candidate_identity": "61b4c89e4ec65ac211debc034ed35f47f79a2757551266a90fadf5acde270773",
        "candidate_raw_sha256": "e00b1b83507ece1808445a3f6cfd07286ee20eecc6f4208d9aa4940ab2fbc1a9",
        "candidate_git_blob_oid_sha1": "4d0aa51522e56038826badd4ae180cdcfe4499e1",
        "creative_premise_family_id": "bc1ebc6a748fad7bcb3c8526b7568b5f30beefd15848db98aadc44f986c74994",
        "g03_commit": COMMIT, "g03_validity": g03["g03_validity"],
        "g03_reconciliation": reconciliation["reconciliation_classification"],
        "g03_receipt_identity": g03["g03_receipt_identity"], "reconciliation_identity": reconciliation["reconciliation_identity"],
        "blind_pass_freeze_commit": "129b32d884e99600b9c5547321b60d04599392fd",
        "sealed_target": reconciliation["sealed_target"]["frozen_plan_option"],
        "target_dominant_recovery_established": False,
        "disposition": "DEVELOPMENT_NONPOSITIVE_AMBIGUOUS_CONFUSABLE_EVIDENCE",
        "partition": "DEVELOPMENT", "evidence_role": "NONPOSITIVE_AMBIGUOUS_CONFUSABLE",
        "positive_m13_coverage_eligible": False, "positive_pool_eligible": False,
        "blind_results": {
            "open_pass": {"dominant": open_pass["primary_mechanism_description"], "supporting": open_pass["supporting_mechanisms"], "confidence": open_pass["confidence"]},
            "contrast_pass": {"dominant": contrast["primary_choice"], "supporting": contrast["supporting_choices"], "confidence": contrast["confidence"]},
        },
        "substantive_disagreement": "WHETHER_ABSURD_CAUSAL_LITERAL_EXTENSION_IS_DOMINANT_OR_IS_LOCAL_SUPPORT_FOR_REVERSE_ORDER_MISDIRECTION",
        "shortcut_findings_preserved": {"open": open_pass["shortcut_assessment"], "contrast": contrast["shortcut_assessment"]},
        "permitted_future_development_diagnostics": ["M13_VERSUS_MISDIRECTION_SEPARABILITY", "LITERALIZATION_SUPPORT_ANALYSIS",
                                                       "REVERSE_DISCLOSURE_ORDER_EFFECT", "ASSIGNMENT_OBLIGATION_REDESIGN", "FUTURE_CONFUSABLE_SET_DESIGN"],
        "candidate_bytes_modified": False, "blind_passes_reinterpreted": False,
        "visibility": "NON_MODEL_VISIBLE", "training_eligibility": False, "runtime_eligibility": False, "production_eligibility": False,
        "authority_matrix": {key: False for key in ("positive_m13_coverage", "positive_pool_evidence", "g03b", "g03c", "g04a", "g04b_pool_certification",
                                                               "voice_review", "owner_positive_review", "repair", "rewrite", "regeneration", "replacement_construction",
                                                               "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    disposition = {**core, "disposition_identity": seal("B2_DEVELOPMENT_PILOT06_AMBIGUOUS_DISPOSITION_V1", core)}
    OUTPUT.write_text(json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"disposition": disposition["disposition"], "disposition_identity": disposition["disposition_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
