"""Freeze the blind Romanian-naturalness review for Pilot 04 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G03C_COMMIT = "b05f474010556215ca6b7f274609f1ed4883d570"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-v1.txt"
G03C_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-g03c-receipt-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G03C_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G03C_COMMIT, "HEAD differs from G03C freeze")
    candidate_bytes = subprocess.check_output(["git", "show", f"{G03C_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    g03c = load(G03C_RECEIPT_PATH)
    require(hashlib.sha256(candidate_bytes).hexdigest() == g03c["candidate_raw_sha256"], "candidate bytes")
    require(g03c["g03c_verdict"] == "CANDIDATE_SHORTCUT_PASS_AND_POOL_G04B_PREREQUISITES_PENDING", "G03C verdict")
    require(g03c["g03c_diagnostic_identity"] == "3ace56a63eced1ae336e0373bde0b97df663e86882760fe839682753e94d21c8", "diagnostic identity")
    require(g03c["g03c_receipt_identity"] == "06b3edd39fff5cf71267fd4298ee5d6c2e154758b0d899b1cc4d204c65fdd06d", "receipt identity")
    require(candidate_bytes.endswith(b"\n") and not candidate_bytes.startswith(b"\xef\xbb\xbf"), "candidate encoding")
    candidate = candidate_bytes.decode("utf-8").rstrip("\n")

    core = {
        "schema_name": "batch2-development-pilot04-candidate01-g04a-romanian-naturalness-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g03c["candidate_identity"],
        "candidate_raw_sha256": g03c["candidate_raw_sha256"],
        "g03c_commit": G03C_COMMIT,
        "g03c_receipt_identity": g03c["g03c_receipt_identity"],
        "g03c_diagnostic_identity": g03c["g03c_diagnostic_identity"],
        "review_mode": "BLIND_ROMANIAN_SURFACE_ONLY",
        "evaluator_visible": {
            "candidate_surface": candidate,
            "rubric": ["BASIC_GRAMMATICALITY", "IDIOMATIC_WORD_ORDER_AND_REGISTER", "NO_CALQUE", "NATURAL_CREATIVE_MARKING", "NO_FORCED_WORDPLAY", "COHESION_AND_PUNCTUATION"],
        },
        "evaluator_inaccessible": [
            "sealed assignment mapping", "mechanism identity/name/ordinal", "constructor packet and prompt",
            "owner preference history", "historical examples", "blind-evaluation material", "Voice rubric and judgment",
        ],
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "findings": {
            "basic_grammaticality": {"verdict": "PASS", "finding": "Ambele enunțuri sunt corecte gramatical și ușor de urmărit."},
            "idiomatic_word_order_and_register": {"verdict": "PASS", "finding": "Ordinea cuvintelor, gerunziul «neputând» și progresia de la poartă la demonstrație sunt firești în română."},
            "no_calque": {"verdict": "PASS", "finding": "Nu apare un calc identificabil sau o construcție sintactică străină de română."},
            "natural_creative_marking": {"verdict": "PASS", "finding": "«În povestea expoziției» integrează planul nonfactual în enunț, fără avertisment editorial sau limbaj de guvernanță."},
            "no_forced_wordplay": {"verdict": "PASS_WITH_RESERVATION", "finding": "Repetiția «ajunge/ajunge să» este perceptibilă, dar susține firesc pivotul dintre acces și demonstrație și nu inventează un sens lexical."},
            "cohesion_and_punctuation": {"verdict": "PASS", "finding": "Punctul și virgula separă adecvat cele două trepte, iar gerunziul leagă inteligibil consecința locală de poantă."},
            "overall_naturalness": {"verdict": "PASS", "finding": "Textul este idiomatic, coerent și oralizabil; repetiția funcțională este o rezervă minoră, nu o rigiditate materială."},
        },
        "g04a_verdict": "ROMANIAN_NATURALNESS_PASS",
        "reservations": ["MINOR_FUNCTIONAL_AJUNGE_REPETITION_NONMATERIAL"],
        "candidate_bytes_modified": False,
        "candidate_repair_attempted": False,
        "disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_VOICE_REVIEW_ONLY",
        "performed": {key: False for key in ("voice_review", "owner_review", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing")},
        "authority_matrix": {key: False for key in ("voice_review", "owner_review", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing", "curriculum_promotion", "g04b_pool_certification")},
    }
    review = {**core, "g04a_review_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G04A_NATURALNESS_REVIEW_V1", core)}
    receipt_core = {
        "schema_name": "batch2-development-pilot04-candidate01-g04a-romanian-naturalness-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": core["candidate_identity"],
        "candidate_raw_sha256": core["candidate_raw_sha256"],
        "g03c_receipt_identity": core["g03c_receipt_identity"],
        "g04a_review_identity": review["g04a_review_identity"],
        "g04a_verdict": core["g04a_verdict"],
        "reservations": core["reservations"],
        "candidate_bytes_modified": False,
        "voice_review_performed": False,
        "next_gate_eligible": "VOICE_REVIEW_SEPARATELY_AUTHORIZED_ONLY",
        "authority_matrix": core["authority_matrix"],
    }
    receipt = {**receipt_core, "g04a_receipt_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G04A_NATURALNESS_RECEIPT_V1", receipt_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot04-candidate01-g04a-naturalness-review-v1.json", review), ("humor-mechanics-batch2-development-pilot04-candidate01-g04a-naturalness-receipt-v1.json", receipt)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g04a_verdict": core["g04a_verdict"], "g04a_review_identity": review["g04a_review_identity"], "g04a_receipt_identity": receipt["g04a_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
