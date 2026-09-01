"""Freeze the blind Voice review for Pilot 07 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
G04A_COMMIT = "78c097e3d992d1986ef456d9773d9479f5ac32c8"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
G04A_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g04a-naturalness-receipt-v1.json"
CANNED_MARKER = "Într-o continuare imaginară"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{G04A_COMMIT}:{path}"], cwd=ROOT)


def tracked_text(path: str) -> str:
    return git_bytes(path).decode("utf-8")


def write_json(name: str, value: dict[str, Any]) -> None:
    (ARTIFACTS / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G04A_COMMIT, "HEAD differs from the authorized G04A commit")
    candidate_bytes = git_bytes(CANDIDATE_PATH)
    g04a = json.loads(git_bytes(G04A_RECEIPT_PATH))
    require(hashlib.sha256(candidate_bytes).hexdigest() == g04a["candidate_raw_sha256"], "candidate bytes")
    require(g04a["g04a_verdict"] == "ROMANIAN_NATURALNESS_PASS", "G04A verdict")
    require(g04a["g04a_review_identity"] == "3b07ed9ad96564086c679ba47d2a4dd1659f09c3cd28e18a0018c74fec49011f", "G04A review")
    require(g04a["g04a_receipt_identity"] == "73c42b8de567adf59a68f4c7615bbdaae46f2e77d7b047fa6d7c230ed60e56eb", "G04A receipt")
    require(candidate_bytes.endswith(b"\n") and not candidate_bytes.startswith(b"\xef\xbb\xbf"), "candidate encoding")
    candidate = candidate_bytes.decode("utf-8").rstrip("\n")

    comparison_paths = [
        "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-v1.txt",
        "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-v1.txt",
    ]
    exact_marker_matches = [path for path in comparison_paths if CANNED_MARKER in tracked_text(path)]
    require(CANNED_MARKER in candidate, "Pilot 07 marker absent")
    require(exact_marker_matches == comparison_paths, "cross-pilot exact-marker scan")

    authority_matrix = {
        key: False
        for key in (
            "owner_review",
            "g04b_pool_certification",
            "candidate_repair",
            "candidate_rewrite",
            "candidate_regeneration",
            "curriculum_promotion",
            "training",
            "runtime_integration",
            "production_routing",
        )
    }
    core = {
        "schema_name": "batch2-development-pilot07-candidate01-blind-voice-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g04a["candidate_identity"],
        "candidate_raw_sha256": g04a["candidate_raw_sha256"],
        "g04a_commit": G04A_COMMIT,
        "g04a_review_identity": g04a["g04a_review_identity"],
        "g04a_receipt_identity": g04a["g04a_receipt_identity"],
        "g04a_reservations": g04a["reservations"],
        "review_mode": "BLIND_MECHANISM_INDEPENDENT_VOICE_COMPATIBILITY",
        "evaluator_visible": {
            "candidate_surface": candidate,
            "rubric": [
                "TONAL_COHERENCE",
                "SENTENCE_MOVEMENT",
                "PAYOFF_ECONOMY",
                "VOICE_SPECIFICITY_WITHOUT_OVERWRITING",
                "NO_CANNED_OPENING_OR_TRANSITION",
                "NO_CANNED_LANDING",
                "NO_HISTORICAL_WORDING_COPY",
                "REGISTER_RESERVATION_MATERIALITY",
            ],
            "mechanical_exact_match_result": {
                "matched_phrase": CANNED_MARKER,
                "prior_development_candidate_ids": ["PILOT05", "PILOT06"],
                "prior_surfaces_exposed": False,
            },
        },
        "evaluator_inaccessible": [
            "sealed assignment mapping",
            "mechanism identity, name, or ordinal",
            "G03 target reconciliation",
            "constructor packet and prompt",
            "owner preference history",
            "historical candidate surfaces",
            "blind-evaluation material",
            "future owner judgment",
        ],
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "owner_preference_accessed": False,
        "historical_surfaces_exposed_to_evaluator": False,
        "findings": {
            "tonal_coherence": {
                "verdict": "PASS",
                "finding": "Tonul rămâne sec și controlat, de la constatarea factuală la ciclul imaginar.",
            },
            "sentence_movement": {
                "verdict": "PASS",
                "finding": "Prima frază fixează situația; a doua înaintează lizibil prin rubrică, analiză, reinscriere și acumulare.",
            },
            "payoff_economy": {
                "verdict": "PASS",
                "finding": "Finalul despre raportul mai lung decât verificarea închide progresia fără explicație post-poantă.",
            },
            "voice_specificity_without_overwriting": {
                "verdict": "PASS_WITH_RESERVATION",
                "finding": "Vocabularul raportului și al rubricii este contextual, dar densitatea nominală păstrează o ușoară rigiditate procedurală.",
            },
            "no_canned_opening_or_transition": {
                "verdict": "FAIL",
                "finding": "Tranziția exactă «Într-o continuare imaginară» este reutilizată în candidații DEVELOPMENT Pilot 05 și Pilot 06; funcționează ca marcaj de construcție interschimbabil, nu ca alegere de voce specifică familiei.",
            },
            "no_canned_landing": {
                "verdict": "PASS",
                "finding": "Aterizarea depinde de raport, analiză și creșterea recursivă; nu este un slogan interschimbabil.",
            },
            "no_historical_wording_copy": {
                "verdict": "FAIL_PARTIAL_EXACT_TEMPLATE_REUSE",
                "finding": "Scanarea mecanică găsește aceeași tranziție în două familii DEVELOPMENT anterioare. Nu există dovadă de copiere a întregii suprafețe, însă fragmentul repetat este material pentru Voice și pentru rezistența la șabloane.",
            },
            "register_reservation_materiality": {
                "verdict": "MIXED",
                "finding": "Repetiția nominală rămâne nematerială singură; marcajul editorial devine material când este pus în relație cu reutilizarea exactă între piloți.",
            },
            "overall_voice_compatibility": {
                "verdict": "FAIL",
                "finding": "Mișcarea și poanta sunt controlate, dar tranziția reutilizată introduce o amprentă de șablon incompatibilă cu cerința de Voice distinctă și robustă la shortcut-uri.",
            },
        },
        "voice_verdict": "VOICE_REJECTED",
        "stable_rejection_reasons": ["CANNED_CROSS_PILOT_CREATIVE_TRANSITION_REUSE"],
        "preserved_nonmaterial_reservations": ["MINOR_PROCEDURAL_NOMINAL_REPETITION_NONMATERIAL"],
        "materialized_g04a_reservation": "MINOR_EDITORIAL_CREATIVE_MARKER_BECOMES_MATERIAL_UNDER_CROSS_PILOT_EXACT_REUSE",
        "candidate_bytes_modified": False,
        "candidate_repair_attempted": False,
        "disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_NONPOSITIVE_VOICE_REJECTION_FREEZE_ONLY",
        "authority_matrix": authority_matrix,
    }
    review = {
        **core,
        "voice_review_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_BLIND_VOICE_REVIEW_V1", core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot07-candidate01-blind-voice-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": core["candidate_identity"],
        "candidate_raw_sha256": core["candidate_raw_sha256"],
        "g04a_receipt_identity": core["g04a_receipt_identity"],
        "voice_review_identity": review["voice_review_identity"],
        "voice_verdict": core["voice_verdict"],
        "stable_rejection_reasons": core["stable_rejection_reasons"],
        "candidate_bytes_modified": False,
        "owner_review_performed": False,
        "next_gate_eligible": "NONPOSITIVE_VOICE_REJECTION_FREEZE_SEPARATELY_AUTHORIZED_ONLY",
        "authority_matrix": authority_matrix,
    }
    receipt = {
        **receipt_core,
        "voice_receipt_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_BLIND_VOICE_RECEIPT_V1", receipt_core),
    }
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-voice-review-v1.json", review)
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-voice-receipt-v1.json", receipt)
    print(json.dumps({
        "voice_verdict": core["voice_verdict"],
        "voice_review_identity": review["voice_review_identity"],
        "voice_receipt_identity": receipt["voice_receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
