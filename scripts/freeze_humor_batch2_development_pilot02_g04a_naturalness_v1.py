"""Freeze the blind Romanian-naturalness review for Pilot 02 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G03C_COMMIT = "5dea3424e8a3dabb5b81f1c7405da4eec272d1da"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"
G03C_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03c-receipt-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def load_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G03C_COMMIT,
        "HEAD differs from G03C freeze",
    )
    candidate_bytes = load_bytes(G03C_COMMIT, CANDIDATE_PATH)
    g03c = load_json(G03C_COMMIT, G03C_RECEIPT_PATH)
    require(hashlib.sha256(candidate_bytes).hexdigest() == g03c["candidate_raw_sha256"], "candidate bytes")
    require(g03c["g03c_verdict"] == "CANDIDATE_SHORTCUT_PASS_AND_POOL_PENDING", "G03C verdict")
    require(
        g03c["g03c_diagnostic_identity"]
        == "1e4646a370d36a3be7978acb0bbf0ac8964143098358924b0c7b0680477842d0",
        "G03C diagnostic identity",
    )
    candidate = candidate_bytes.decode("utf-8")
    require(candidate_bytes.endswith(b"\n") and not candidate_bytes.startswith(b"\xef\xbb\xbf"), "candidate encoding")

    review_core = {
        "schema_name": "batch2-development-pilot02-candidate01-g04a-romanian-naturalness-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g03c["candidate_identity"],
        "candidate_raw_sha256": g03c["candidate_raw_sha256"],
        "g03c_commit": G03C_COMMIT,
        "g03c_receipt_identity": g03c["g03c_receipt_identity"],
        "g03c_diagnostic_identity": g03c["g03c_diagnostic_identity"],
        "review_mode": "BLIND_ROMANIAN_SURFACE_ONLY",
        "evaluator_visible": {
            "candidate_surface": candidate.rstrip("\n"),
            "rubric": [
                "IDIOMATIC_WORD_ORDER_AND_REGISTER",
                "NO_CALQUE",
                "NATURAL_CREATIVE_MARKING",
                "NO_FORCED_WORDPLAY",
            ],
        },
        "evaluator_inaccessible": [
            "sealed assignment mapping",
            "mechanism identity/name/ordinal",
            "constructor packet and prompt",
            "owner preference history",
            "historical examples",
            "blind-evaluation material",
            "Voice rubric and judgment",
        ],
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "findings": {
            "basic_grammaticality": {
                "verdict": "PASS",
                "finding": "Ambele enunțuri sunt inteligibile și nu conțin o eroare gramaticală decisivă.",
            },
            "idiomatic_word_order_and_register": {
                "verdict": "FAIL",
                "finding": "Formularea este rigidă și procedurală; «suspendă ... încheierea testului» și acumularea pasiv-abstractă nu sună ca o continuare românească firească.",
            },
            "no_calque": {
                "verdict": "PASS_WITH_RESERVATION",
                "finding": "Nu este identificat un calc străin precis, dar nominalizarea și metadiscursul contribuie la senzația de text tradus sau administrativ.",
            },
            "natural_creative_marking": {
                "verdict": "FAIL",
                "finding": "«Într-o continuare explicit fictivă» funcționează ca etichetă de guvernanță introdusă în suprafață, nu ca marcaj creativ natural integrat în română.",
            },
            "no_forced_wordplay": {
                "verdict": "PASS",
                "finding": "Nu există joc de cuvinte forțat; problema este registrul și integrarea marcajului fictiv.",
            },
            "overall_naturalness": {
                "verdict": "FAIL",
                "finding": "Sensul este recuperabil, dar marcajul metadiscursiv și registrul procedural sunt material nenaturale.",
            },
        },
        "g04a_verdict": "ROMANIAN_NATURALNESS_REJECTED",
        "stable_rejection_reasons": [
            "UNNATURAL_GOVERNANCE_STYLE_CREATIVE_MARKER",
            "PROCEDURAL_ABSTRACT_REGISTER",
        ],
        "candidate_bytes_modified": False,
        "candidate_repair_attempted": False,
        "disposition_effect": "STOP_BEFORE_VOICE_OR_OWNER_REVIEW_UNLESS_SEPARATELY_GOVERNED_AS_DIAGNOSTIC",
        "performed": {
            "voice_review": False,
            "owner_review": False,
            "candidate_repair": False,
            "candidate_rewrite": False,
            "candidate_regeneration": False,
            "training": False,
            "runtime_integration": False,
            "production_routing": False,
        },
        "authority_matrix": {
            key: False
            for key in (
                "voice_review",
                "owner_review",
                "candidate_repair",
                "candidate_rewrite",
                "candidate_regeneration",
                "training",
                "runtime_integration",
                "production_routing",
                "curriculum_promotion",
            )
        },
    }
    review = {
        **review_core,
        "g04a_review_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G04A_NATURALNESS_REVIEW_V1", review_core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot02-candidate01-g04a-romanian-naturalness-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": review_core["candidate_identity"],
        "candidate_raw_sha256": review_core["candidate_raw_sha256"],
        "g03c_receipt_identity": review_core["g03c_receipt_identity"],
        "g04a_review_identity": review["g04a_review_identity"],
        "g04a_verdict": review_core["g04a_verdict"],
        "stable_rejection_reasons": review_core["stable_rejection_reasons"],
        "candidate_bytes_modified": False,
        "voice_review_performed": False,
        "next_action": "FREEZE_DEVELOPMENT_NONPOSITIVE_NATURALNESS_REJECTION_OR_SEPARATELY_AUTHORIZE_DIAGNOSTIC_VOICE_REVIEW",
        "authority_matrix": review_core["authority_matrix"],
    }
    receipt = {
        **receipt_core,
        "g04a_receipt_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G04A_NATURALNESS_RECEIPT_V1", receipt_core),
    }
    for name, value in (
        ("humor-mechanics-batch2-development-pilot02-candidate01-g04a-naturalness-review-v1.json", review),
        ("humor-mechanics-batch2-development-pilot02-candidate01-g04a-naturalness-receipt-v1.json", receipt),
    ):
        (ART / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({
        "g04a_verdict": receipt["g04a_verdict"],
        "g04a_review_identity": review["g04a_review_identity"],
        "g04a_receipt_identity": receipt["g04a_receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
