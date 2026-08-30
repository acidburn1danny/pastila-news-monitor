"""Freeze the non-positive ambiguous DEVELOPMENT disposition for Pilot 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
G03_COMMIT = "6ef856dfabced08cb482500e463cd9b83f7d710c"
BASE = "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-g03-"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-disposition-v1.json"


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G03_COMMIT}:{path}"], cwd=ROOT))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("disposition already frozen")
    pass_a = git_json(BASE + "pass-a-v1.json")
    pass_b = git_json(BASE + "pass-b-v1.json")
    reconciliation = git_json(BASE + "reconciliation-v1.json")
    g03 = git_json(BASE + "receipt-v1.json")
    assert pass_a["result"]["primary_mechanism"] == "PERSONIFICATION"
    assert pass_a["result"]["primary_role"] == "DOMINANT"
    assert pass_a["result"]["supporting_mechanisms"] == ["ABSURDITY", "EXTENDED_METAPHOR"]
    assert pass_a["result"]["confidence"] == "HIGH"
    assert pass_b["result"]["primary_choice"] == "ABSURD_LOGICAL_EXTENSION"
    assert pass_b["result"]["primary_role"] == "DOMINANT"
    assert pass_b["result"]["supporting_choices"] == ["ESCALATION"]
    assert pass_b["result"]["confidence"] == "HIGH"
    assert reconciliation["classification"] == "AMBIGUOUS_MECHANISM"
    assert g03["g03_validity"] == "VALID_BLIND_REVIEW"
    assert g03["g03_receipt_identity"] == "71c3ed0b4cc572c6988785ab9c4ce74d01a54bd71d14e89d48c8158a25f6d1cd"
    core = {
        "schema_name": "batch2-development-pilot01-ambiguous-disposition-v1",
        "schema_version": "1.0.0",
        "candidate_identity": "f96e626487812b4a9ad32ef548d4ac715fae4ea9bb24590a73f942b0783f080f",
        "candidate_raw_sha256": "2f848e2bc9d87b113df95996a4d49d48fbe4334d6c204ef707664158e23caf9d",
        "g02_verdict": "PASS",
        "g02_identity": "bc6e7ce8975f94ad43de4cbc99b209099f6c330d8d53e85882fb356348d0d210",
        "g03_commit": G03_COMMIT,
        "g03_validity": g03["g03_validity"],
        "g03_reconciliation": reconciliation["classification"],
        "g03_receipt_identity": g03["g03_receipt_identity"],
        "sealed_target": "ABSURD_LOGICAL_EXTENSION",
        "target_dominant_recovery_established": False,
        "disposition": "DEVELOPMENT_NONPOSITIVE_AMBIGUOUS_CONFUSABLE_EVIDENCE",
        "partition": "DEVELOPMENT",
        "evidence_role": "NONPOSITIVE_AMBIGUOUS_CONFUSABLE",
        "positive_m13_coverage_eligible": False,
        "blind_results": {
            "pass_a": {
                "dominant": pass_a["result"]["primary_mechanism"],
                "supporting": pass_a["result"]["supporting_mechanisms"],
                "confidence": pass_a["result"]["confidence"],
                "occupational_vocabulary_shortcut_finding": pass_a["result"]["shortcut_dependence"]["lexical"],
            },
            "pass_b": {
                "dominant": pass_b["result"]["primary_choice"],
                "supporting": pass_b["result"]["supporting_choices"],
                "confidence": pass_b["result"]["confidence"],
                "lexical_shortcut_finding": pass_b["result"]["shortcut_dependence"]["lexical"],
            },
        },
        "substantive_disagreement": "WHETHER_EMPLOYMENT_TIMESHEET_FRAMING_IS_THE_DOMINANT_OPERATION_OR_IMPLEMENTS_A_PREMISE_TO_ABSURD_CONSEQUENCE_CHAIN",
        "conflicting_shortcut_judgments": True,
        "permitted_future_development_diagnostics": [
            "M13_VERSUS_PERSONIFICATION_SEPARABILITY",
            "MIXED_MECHANISM_ANALYSIS",
            "ASSIGNMENT_OBLIGATION_REDESIGN",
            "SHORTCUT_DIAGNOSTICS",
            "FUTURE_CONFUSABLE_SET_DESIGN",
        ],
        "candidate_bytes_modified": False,
        "blind_passes_reinterpreted": False,
        "visibility": "NON_MODEL_VISIBLE",
        "authority_matrix": {key: False for key in (
            "positive_m13_coverage", "g03b", "g03c", "g04", "voice_review", "owner_positive_review",
            "repair", "rewrite", "regeneration", "replacement_construction", "model_exposure", "training",
            "runtime_integration", "production_routing")},
    }
    receipt = {**core, "disposition_identity": seal("B2_DEVELOPMENT_PILOT01_AMBIGUOUS_DISPOSITION_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"disposition": receipt["disposition"], "disposition_identity": receipt["disposition_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
