"""Freeze the blind Voice-compatibility review for Pilot 03 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G04A_COMMIT = "70a44fc5dca0508f7c112616f743dc47ec31a8a9"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-v1.txt"
G04A_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-g04a-naturalness-receipt-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G04A_COMMIT, "HEAD differs from G04A freeze")
    candidate_bytes = subprocess.check_output(["git", "show", f"{G04A_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    g04a = json.loads(subprocess.check_output(["git", "show", f"{G04A_COMMIT}:{G04A_RECEIPT_PATH}"], cwd=ROOT))
    require(hashlib.sha256(candidate_bytes).hexdigest() == g04a["candidate_raw_sha256"], "candidate bytes")
    require(g04a["g04a_verdict"] == "ROMANIAN_NATURALNESS_PASS", "G04A verdict")
    require(g04a["g04a_review_identity"] == "3097dea8d17df534cb00bca92e2e771364da8db4637a9c90747bdb2aade81ef4", "G04A review")
    require(g04a["g04a_receipt_identity"] == "eed6c29e2ca003f892ddee1f98c475fd536053662f56049ef6c673ffb5bcfe51", "G04A receipt")
    require(candidate_bytes.endswith(b"\n") and not candidate_bytes.startswith(b"\xef\xbb\xbf"), "candidate encoding")
    candidate = candidate_bytes.decode("utf-8").rstrip("\n")

    core = {
        "schema_name": "batch2-development-pilot03-candidate01-blind-voice-review-v1",
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
                "TONAL_COHERENCE", "SENTENCE_MOVEMENT", "PAYOFF_ECONOMY", "VOICE_SPECIFICITY_WITHOUT_OVERWRITING",
                "NO_CANNED_OPENING", "NO_CANNED_LANDING", "NO_HISTORICAL_WORDING_COPY", "REGISTER_RESERVATION_MATERIALITY",
            ],
        },
        "evaluator_inaccessible": [
            "sealed assignment mapping", "mechanism identity/name/ordinal", "G03 target reconciliation",
            "constructor packet and prompt", "owner preference history", "historical positive or rejected surfaces",
            "blind-evaluation material", "future owner judgment",
        ],
        "sealed_mapping_accessed": False,
        "mechanism_adjudication_performed": False,
        "owner_preference_accessed": False,
        "findings": {
            "tonal_coherence": {"verdict": "PASS", "finding": "Tonul rămâne sec și controlat: constatarea neutră trece într-o logică imaginară fără schimbare bruscă de persoană sau atitudine."},
            "sentence_movement": {"verdict": "PASS", "finding": "Prima frază fixează limita factuală; a doua avansează în două trepte clare și aterizează pe reclasificarea finală."},
            "payoff_economy": {"verdict": "PASS", "finding": "Finalul «singurul lucru care mai poate fi inventariat» închide premisa fără explicație suplimentară după poantă."},
            "voice_specificity_without_overwriting": {"verdict": "PASS", "finding": "Vocabularul de inventar este specific situației și suficient de sobru; nu adaugă ornamente sau o voce teatrală străină materialului."},
            "no_canned_opening": {"verdict": "PASS", "finding": "Deschiderea este o limită factuală legată direct de sursă, nu o formulă generică de introducere comică."},
            "no_canned_landing": {"verdict": "PASS", "finding": "Aterizarea depinde de inventar și de deschiderea coletului; nu este o concluzie interschimbabilă ori un slogan."},
            "no_historical_wording_copy": {"verdict": "PASS", "finding": "Nu există reutilizare de suprafață istorică în linia de construcție; verificarea de expresie exactă găsește frazele doar în artefactele propriei linii Pilot 03."},
            "register_reservation_materiality": {"verdict": "NONMATERIAL", "finding": "Nominalizarea ușor abstractă observată la G04A nu încetinește decisiv ritmul și este compensată de verbul concret și aterizarea scurtă."},
            "overall_voice_compatibility": {"verdict": "PASS", "finding": "Candidatul are setup sobru, progresie lizibilă și payoff contextual, fără deschidere sau aterizare de șablon."},
        },
        "voice_verdict": "VOICE_PASS",
        "reservations": ["MINOR_ABSTRACT_NOMINALIZATION_NONMATERIAL"],
        "candidate_bytes_modified": False,
        "candidate_repair_attempted": False,
        "disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_OWNER_REVIEW_SUBJECT_TO_POOL_PENDING_STATUS",
        "performed": {key: False for key in ("owner_review", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing")},
        "authority_matrix": {key: False for key in ("owner_review", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing", "curriculum_promotion")},
    }
    review = {**core, "voice_review_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_BLIND_VOICE_REVIEW_V1", core)}
    receipt_core = {
        "schema_name": "batch2-development-pilot03-candidate01-blind-voice-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": core["candidate_identity"],
        "candidate_raw_sha256": core["candidate_raw_sha256"],
        "g04a_receipt_identity": core["g04a_receipt_identity"],
        "voice_review_identity": review["voice_review_identity"],
        "voice_verdict": core["voice_verdict"],
        "reservations": core["reservations"],
        "candidate_bytes_modified": False,
        "owner_review_performed": False,
        "next_gate_eligible": "OWNER_REVIEW_SEPARATELY_AUTHORIZED_WITH_POOL_PENDING_EXPLICIT",
        "authority_matrix": core["authority_matrix"],
    }
    receipt = {**receipt_core, "voice_receipt_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_BLIND_VOICE_RECEIPT_V1", receipt_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot03-candidate01-voice-review-v1.json", review), ("humor-mechanics-batch2-development-pilot03-candidate01-voice-receipt-v1.json", receipt)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"voice_verdict": core["voice_verdict"], "voice_review_identity": review["voice_review_identity"], "voice_receipt_identity": receipt["voice_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
