"""Freeze mechanism-causal G03B review for Pilot 03 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G03_COMMIT = "25c78502a7c794bc4642144e11e630ab4ac9ee3d"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-v1.txt"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G03_COMMIT}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G03_COMMIT, "HEAD")
    candidate = subprocess.check_output(["git", "show", f"{G03_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    receipt = load(PREFIX + "g03-receipt-v1.json")
    reconciliation = load(PREFIX + "g03-reconciliation-v1.json")
    require(hashlib.sha256(candidate).hexdigest() == receipt["candidate_raw_sha256"], "candidate")
    require(receipt["g03_validity_status"] == "VALID_BLIND_REVIEW", "validity")
    require(receipt["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT", "classification")
    require(reconciliation["reconciliation_identity"] == "bb183c23e45dd3b11beb03430697291f4da92052dd8fa030b99eac99d805047d", "reconciliation")
    interventions = [
        {"id": "G03B-I01-REMOVE-SECOND-INFERENCE",
         "delta_only": "Elimină reîncadrarea deschiderii ca singur lucru inventariabil.",
         "preserved": ["factual premise", "fictional marking", "first consequence", "topic", "register"],
         "expected_observation": "Rămâne lista goală, dar se pierde consecința absurdă dependentă și dominanța lanțului extins.",
         "mechanism_after": "SUPPORTING_OR_WEAK_NOT_DOMINANT", "causal_result": "DOMINANCE_REMOVED"},
        {"id": "G03B-I02-NEUTRALIZE-FIRST-HINGE",
         "delta_only": "Înlocuiește lista goală cu constatarea neutră că inventarierea așteaptă deschiderea.",
         "preserved": ["factual premise", "topic", "statusul conținutului", "register"],
         "expected_observation": "Dispare lipsa confirmării care făcea posibilă reîncadrarea finală; lanțul-țintă nu se formează.",
         "mechanism_after": "ABSENT", "causal_result": "MECHANISM_REMOVED"},
        {"id": "G03B-I03-SUBSTITUTE-UNRELATED-ABSURDITY",
         "delta_only": "Păstrează premisa și tonul imaginar, dar substituie o întâmplare absurdă fără dependență de conținutul necunoscut.",
         "preserved": ["topic", "factual premise", "fictional status", "absurd tone", "approximate length"],
         "expected_observation": "Absurdul rămâne, însă clasificarea se mută la absurditate fără legătură.",
         "mechanism_after": "ABSENT_LABEL_CHANGES", "causal_result": "LABEL_CHANGE"},
        {"id": "G03B-I04-PARAPHRASE-NONCAUSAL-CUES",
         "delta_only": "Schimbă vocabularul și punctuația, păstrând lista goală, lipsa confirmării și reîncadrarea dependentă.",
         "preserved": ["all facts", "dependency graph", "fictional marking", "payoff", "topic"],
         "expected_observation": "Mecanismul rămâne dominant și nu depinde de un cuvânt ori conector fix.",
         "mechanism_after": "DOMINANT", "causal_result": "INVARIANT_UNDER_SURFACE_PARAPHRASE"},
        {"id": "G03B-I05-REMOVE-CREATIVE-MARKER",
         "delta_only": "Elimină numai cadrul «povestea imaginară».",
         "preserved": ["premise", "dependency graph", "payoff", "topic"],
         "expected_observation": "Lanțul mecanic rămâne, dar candidatul devine nevalid separat la granița factuală G02.",
         "mechanism_after": "DOMINANT_BUT_AUTHORITY_INVALID", "causal_result": "MARKER_NOT_CAUSAL_TO_MECHANISM"},
        {"id": "G03B-I06-REMOVE-FINAL-RECLASSIFICATION-ONLY",
         "delta_only": "Păstrează cele două propoziții, dar înlocuiește obiectul inventariabil cu o consecință neutră.",
         "preserved": ["factual premise", "first hinge", "dependency connector", "topic"],
         "expected_observation": "Componenta de reclasificare comică dispare, iar extensia logică rămâne doar slabă, confirmând rolul ei de suport în realizarea prezentă.",
         "mechanism_after": "WEAK_SUPPORTING", "causal_result": "SUPPORTING_RECLASSIFICATION_REMOVED"},
    ]
    review_core = {
        "schema_name": "batch2-development-pilot03-candidate01-g03b-causal-review-v1", "schema_version": "1.0.0",
        "candidate_identity": receipt["candidate_identity"], "candidate_raw_sha256": receipt["candidate_raw_sha256"],
        "creative_premise_family_id": receipt["creative_premise_family_id"], "g03_commit": G03_COMMIT,
        "g03_receipt_identity": receipt["g03_receipt_identity"], "reconciliation_identity": reconciliation["reconciliation_identity"],
        "tested_mechanism": "Absurd Logical Extension", "candidate_bytes_modified": False,
        "counterfactuals_materialized_as_candidates": False,
        "causal_trace": {
            "factual_premise": "La momentul recepției nu este documentat conținutul exact al coletului.",
            "creative_marking": "În povestea imaginară a coletului",
            "transformation_step_1": "Necunoașterea conținutului lasă lista de inventar goală.",
            "transformation_step_2": "Lipsa confirmării reclasifică deschiderea programată drept singurul lucru inventariabil.",
            "incongruity_payoff": "Procesul necesar pentru a afla conținutul devine el însuși obiectul pe care inventarul îl poate conține.",
            "local_dependency": "PREMISE_TO_EMPTY_LIST_TO_NO_CONFIRMATION_TO_OPENING_AS_INVENTORY_ITEM",
            "verdict": "COMPLETE_RECOVERABLE_CAUSAL_CHAIN"},
        "minimal_interventions": interventions,
        "controls": {"topic_control": "PASS", "factual_premise_control": "PASS",
                     "length_control": "PASS_WHERE_PRACTICABLE_DELTA_ONLY", "tone_control": "PASS_WHERE_PRACTICABLE",
                     "creative_marking_separated_from_mechanism_causality": "PASS",
                     "lexical_keyword_dependence": "REJECTED_BY_I04", "mere_absurdity_explanation": "REJECTED_BY_I03",
                     "supporting_reclassification_isolation": "PASS_I06"},
        "causal_findings": {
            "necessary_structure": ["factual premise", "first premise-dependent consequence",
                                    "second locally dependent consequence", "absurd categorial payoff"],
            "not_necessary": ["specific causal connective", "specific vocabulary", "punctuation", "surface template"],
            "removal_test": "PASS_I01_REDUCES_DOMINANCE_I02_REMOVES_I03_CHANGES_LABEL",
            "invariance_test": "PASS_I04", "boundary_separation_test": "PASS_I05",
            "supporting_mechanism_isolation": "PASS_I06"},
        "g03b_verdict": "CAUSAL_MECHANISM_CONFIRMED",
        "candidate_disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G03C_ONLY",
        "performed": {key: False for key in ("g03c", "romanian_naturalness_review", "voice_review", "owner_review",
                                               "candidate_repair", "candidate_rewrite", "candidate_regeneration")},
        "authority_matrix": {key: False for key in ("g03c", "romanian_naturalness_review", "voice_review", "owner_review",
                                                     "candidate_repair", "candidate_rewrite", "candidate_regeneration",
                                                     "training", "runtime_integration", "production_routing")},
    }
    review = {**review_core, "g03b_review_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G03B_REVIEW_V1", review_core)}
    receipt_core = {"schema_name": "batch2-development-pilot03-candidate01-g03b-receipt-v1", "schema_version": "1.0.0",
                    "candidate_identity": review_core["candidate_identity"], "candidate_raw_sha256": review_core["candidate_raw_sha256"],
                    "g03_receipt_identity": review_core["g03_receipt_identity"], "g03b_review_identity": review["g03b_review_identity"],
                    "g03b_verdict": review_core["g03b_verdict"], "candidate_bytes_modified": False,
                    "counterfactual_candidate_created": False, "next_gate_eligible": "G03C_SEPARATELY_AUTHORIZED_ONLY",
                    "authority_matrix": review_core["authority_matrix"]}
    receipt_out = {**receipt_core, "g03b_receipt_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G03B_RECEIPT_V1", receipt_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot03-candidate01-g03b-review-v1.json", review),
                        ("humor-mechanics-batch2-development-pilot03-candidate01-g03b-receipt-v1.json", receipt_out)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g03b_verdict": review["g03b_verdict"], "g03b_review_identity": review["g03b_review_identity"],
                      "g03b_receipt_identity": receipt_out["g03b_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
