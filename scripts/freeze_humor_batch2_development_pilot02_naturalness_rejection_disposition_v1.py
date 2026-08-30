"""Freeze Pilot 02 candidate 01 as non-positive naturalness-rejection evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G04A_COMMIT = "0d3f8255f6a990f9ec8ef6814b637f664c633c6e"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"
G04A_REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g04a-naturalness-review-v1.json"
G04A_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g04a-naturalness-receipt-v1.json"
G03_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03-receipt-v1.json"
G03B_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03b-receipt-v1.json"
G03C_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03c-receipt-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G04A_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G04A_COMMIT,
        "HEAD differs from G04A freeze",
    )
    candidate = subprocess.check_output(["git", "show", f"{G04A_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    review = load_json(G04A_REVIEW_PATH)
    g04a = load_json(G04A_RECEIPT_PATH)
    g03 = load_json(G03_RECEIPT_PATH)
    g03b = load_json(G03B_RECEIPT_PATH)
    g03c = load_json(G03C_RECEIPT_PATH)
    require(hashlib.sha256(candidate).hexdigest() == g04a["candidate_raw_sha256"], "candidate bytes")
    require(g04a["g04a_verdict"] == "ROMANIAN_NATURALNESS_REJECTED", "G04A verdict")
    require(
        g04a["g04a_review_identity"]
        == "29010c18bfe5e5534a7827571f7b615ab7b4215b7f542078dfcad4c6c55d53f2",
        "G04A review identity",
    )
    require(
        g04a["g04a_receipt_identity"]
        == "217dcefb73ef45ad0357f64f37739091657484a299b93e3fc01c9f7a4d5ebc71",
        "G04A receipt identity",
    )
    require(
        g04a["stable_rejection_reasons"]
        == ["UNNATURAL_GOVERNANCE_STYLE_CREATIVE_MARKER", "PROCEDURAL_ABSTRACT_REGISTER"],
        "stable rejection reasons",
    )

    core = {
        "schema_name": "batch2-development-pilot02-candidate01-naturalness-rejection-disposition-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g04a["candidate_identity"],
        "candidate_raw_sha256": g04a["candidate_raw_sha256"],
        "creative_premise_family_id": g03["creative_premise_family_id"],
        "partition": "DEVELOPMENT",
        "disposition": "DEVELOPMENT_NONPOSITIVE_ROMANIAN_NATURALNESS_REJECTION_EVIDENCE",
        "evidence_role": "NONPOSITIVE_NATURALNESS_REJECTION",
        "visibility": "NON_MODEL_VISIBLE",
        "bound_lineage": {
            "g03_validity": g03["g03_validity_status"],
            "g03_reconciliation": g03["reconciliation_classification"],
            "g03_receipt_identity": g03["g03_receipt_identity"],
            "g03b_verdict": g03b["g03b_verdict"],
            "g03b_receipt_identity": g03b["g03b_receipt_identity"],
            "g03c_verdict": g03c["g03c_verdict"],
            "g03c_receipt_identity": g03c["g03c_receipt_identity"],
            "g04a_verdict": g04a["g04a_verdict"],
            "g04a_review_identity": g04a["g04a_review_identity"],
            "g04a_receipt_identity": g04a["g04a_receipt_identity"],
            "g04a_commit": G04A_COMMIT,
        },
        "stable_rejection_reasons": g04a["stable_rejection_reasons"],
        "frozen_naturalness_findings": {
            "basic_grammaticality": review["findings"]["basic_grammaticality"]["verdict"],
            "idiomatic_word_order_and_register": review["findings"]["idiomatic_word_order_and_register"]["verdict"],
            "natural_creative_marking": review["findings"]["natural_creative_marking"]["verdict"],
            "overall_naturalness": review["findings"]["overall_naturalness"]["verdict"],
        },
        "positive_coverage_eligible": False,
        "curriculum_candidate_eligible": False,
        "permitted_future_development_diagnostics": [
            "CREATIVE_MARKING_NATURALNESS",
            "PROCEDURAL_REGISTER_PRESSURE",
            "OBLIGATION_TO_SURFACE_REGISTER_TRANSFER",
            "FUTURE_NATURALNESS_CONFUSABLE_SET_DESIGN",
        ],
        "candidate_bytes_modified": False,
        "frozen_findings_reinterpreted": False,
        "performed": {
            "voice_review": False,
            "candidate_repair": False,
            "candidate_rewrite": False,
            "candidate_regeneration": False,
            "owner_positive_review": False,
            "training": False,
            "runtime_integration": False,
            "production_routing": False,
        },
        "authority_matrix": {
            key: False
            for key in (
                "voice_review",
                "candidate_repair",
                "candidate_rewrite",
                "candidate_regeneration",
                "owner_positive_review",
                "training",
                "runtime_integration",
                "production_routing",
                "curriculum_promotion",
                "positive_coverage",
            )
        },
    }
    disposition = {
        **core,
        "disposition_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_NATURALNESS_REJECTION_DISPOSITION_V1", core),
    }
    path = ART / "humor-mechanics-batch2-development-pilot02-candidate01-naturalness-rejection-disposition-v1.json"
    path.write_text(
        json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "disposition": disposition["disposition"],
        "disposition_identity": disposition["disposition_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
