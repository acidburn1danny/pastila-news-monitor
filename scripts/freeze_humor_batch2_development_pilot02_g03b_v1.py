"""Freeze the mechanism-causal G03B review for Pilot 02 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G03_COMMIT = "1ab974a44973c0068ebc4c82a5037943bba407fb"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"
G03_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03-receipt-v1.json"
RECONCILIATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03-reconciliation-v1.json"


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
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G03_COMMIT,
        "HEAD differs from frozen G03 commit",
    )
    candidate = load_bytes(G03_COMMIT, CANDIDATE_PATH)
    receipt = load_json(G03_COMMIT, G03_RECEIPT_PATH)
    reconciliation = load_json(G03_COMMIT, RECONCILIATION_PATH)
    require(hashlib.sha256(candidate).hexdigest() == receipt["candidate_raw_sha256"], "candidate bytes")
    require(receipt["g03_validity_status"] == "VALID_BLIND_REVIEW", "G03 validity")
    require(receipt["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT", "G03 classification")
    require(
        reconciliation["reconciliation_identity"]
        == "363b92a12412cc1cfedc553b4df3fafb9f7e026d26b92432fccb52d371cccd44",
        "reconciliation identity",
    )

    review_core = {
        "schema_name": "batch2-development-pilot02-candidate01-g03b-causal-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": receipt["candidate_identity"],
        "candidate_raw_sha256": receipt["candidate_raw_sha256"],
        "creative_premise_family_id": receipt["creative_premise_family_id"],
        "g03_commit": G03_COMMIT,
        "g03_receipt_identity": receipt["g03_receipt_identity"],
        "reconciliation_identity": reconciliation["reconciliation_identity"],
        "tested_mechanism": "Absurd Logical Extension",
        "candidate_bytes_modified": False,
        "counterfactuals_materialized_as_candidates": False,
        "causal_trace": {
            "factual_premise": "La încheierea testului nu este stabilit niciun sortiment câștigător.",
            "creative_marking": "continuare explicit fictivă",
            "transformation_step_1": "Lipsa câștigătorului suspendă încheierea testului.",
            "transformation_step_2": "Neîncheierea testului elimină momentul în care câștigătorul trebuia stabilit.",
            "incongruity_payoff": "Consecința extinsă anulează cadrul temporal al premisei din care pornește.",
            "local_dependency": "PREMISE_TO_STEP_1_TO_STEP_2_TO_SELF_CANCELLING_PAYOFF",
            "verdict": "COMPLETE_RECOVERABLE_CAUSAL_CHAIN",
        },
        "minimal_interventions": [
            {
                "id": "G03B-I01-REMOVE-SECOND-INFERENCE",
                "delta_only": "Elimină pasul prin care neîncheierea testului face să dispară momentul stabilirii.",
                "preserved": ["topic", "factual premise", "fictional marking", "first consequence", "tone"],
                "expected_observation": "Rămâne o consecință fictivă, dar se pierde autoanularea și lanțul extins distinctiv.",
                "mechanism_after": "SUPPORTING_OR_WEAK_NOT_DOMINANT",
                "causal_result": "DOMINANCE_REMOVED",
            },
            {
                "id": "G03B-I02-NEUTRALIZE-FIRST-HINGE",
                "delta_only": "Înlocuiește suspendarea încheierii cu consecința neutră că rezultatul rămâne nedeterminat.",
                "preserved": ["topic", "factual premise", "result status", "sentence count where practicable", "register"],
                "expected_observation": "Nu mai există trecerea necesară către dispariția momentului; operația-țintă nu se formează.",
                "mechanism_after": "ABSENT",
                "causal_result": "MECHANISM_REMOVED",
            },
            {
                "id": "G03B-I03-SUBSTITUTE-UNRELATED-ABSURDITY",
                "delta_only": "Păstrează premisa, dar substituie lanțului o consecință absurdă fără dependență inferențială de ea.",
                "preserved": ["topic", "factual premise", "fictional status", "absurd tone", "approximate length"],
                "expected_observation": "Absurdul poate rămâne, însă clasificarea se mută la absurditate fără legătură, nu la extensia logică a premisei.",
                "mechanism_after": "ABSENT_LABEL_CHANGES",
                "causal_result": "LABEL_CHANGE",
            },
            {
                "id": "G03B-I04-PARAPHRASE-NONCAUSAL-CUES",
                "delta_only": "Schimbă doar formulările și conectorii, păstrând cele două dependențe și autoanularea temporală.",
                "preserved": ["all facts", "dependency graph", "fictional marking", "payoff", "topic"],
                "expected_observation": "Mecanismul rămâne dominant; nu depinde de un cuvânt-cheie sau de un conector fix.",
                "mechanism_after": "DOMINANT",
                "causal_result": "INVARIANT_UNDER_SURFACE_PARAPHRASE",
            },
            {
                "id": "G03B-I05-REMOVE-CREATIVE-MARKER",
                "delta_only": "Elimină numai marcajul explicit al continuării fictive.",
                "preserved": ["premise", "dependency graph", "payoff", "topic", "length approximately"],
                "expected_observation": "Operația mecanică rămâne detectabilă, dar candidatul ar încălca separat granița factuală G02.",
                "mechanism_after": "DOMINANT_BUT_AUTHORITY_INVALID",
                "causal_result": "MARKER_NOT_CAUSAL_TO_MECHANISM",
            },
        ],
        "controls": {
            "topic_control": "PASS",
            "factual_premise_control": "PASS",
            "length_control": "PASS_WHERE_PRACTICABLE_DELTA_ONLY",
            "tone_control": "PASS_WHERE_PRACTICABLE",
            "creative_marking_separated_from_mechanism_causality": "PASS",
            "lexical_keyword_dependence": "REJECTED_BY_I04",
            "mere_absurdity_explanation": "REJECTED_BY_I03",
        },
        "causal_findings": {
            "necessary_structure": [
                "factual premise",
                "first premise-dependent consequence",
                "second locally dependent consequence",
                "self-cancelling temporal payoff",
            ],
            "not_necessary": ["specific causal connective", "specific vocabulary", "punctuation", "surface template"],
            "removal_test": "PASS_I01_REDUCES_DOMINANCE_I02_REMOVES_I03_CHANGES_LABEL",
            "invariance_test": "PASS_I04",
            "boundary_separation_test": "PASS_I05",
        },
        "g03b_verdict": "CAUSAL_MECHANISM_CONFIRMED",
        "candidate_disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G03C_ONLY",
        "performed": {
            "g03c": False,
            "romanian_naturalness_review": False,
            "voice_review": False,
            "owner_review": False,
            "candidate_repair": False,
            "candidate_rewrite": False,
            "candidate_regeneration": False,
        },
        "authority_matrix": {
            key: False
            for key in (
                "g03c",
                "romanian_naturalness_review",
                "voice_review",
                "owner_review",
                "candidate_repair",
                "candidate_rewrite",
                "candidate_regeneration",
                "training",
                "runtime_integration",
                "production_routing",
            )
        },
    }
    review = {
        **review_core,
        "g03b_review_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03B_REVIEW_V1", review_core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot02-candidate01-g03b-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": review_core["candidate_identity"],
        "candidate_raw_sha256": review_core["candidate_raw_sha256"],
        "g03_receipt_identity": review_core["g03_receipt_identity"],
        "g03b_review_identity": review["g03b_review_identity"],
        "g03b_verdict": review_core["g03b_verdict"],
        "candidate_bytes_modified": False,
        "counterfactual_candidate_created": False,
        "next_gate_eligible": "G03C_SEPARATELY_AUTHORIZED_ONLY",
        "authority_matrix": review_core["authority_matrix"],
    }
    receipt_out = {
        **receipt_core,
        "g03b_receipt_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03B_RECEIPT_V1", receipt_core),
    }
    outputs = {
        "humor-mechanics-batch2-development-pilot02-candidate01-g03b-review-v1.json": review,
        "humor-mechanics-batch2-development-pilot02-candidate01-g03b-receipt-v1.json": receipt_out,
    }
    for name, value in outputs.items():
        (ART / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(
        json.dumps(
            {
                "g03b_verdict": review["g03b_verdict"],
                "g03b_review_identity": review["g03b_review_identity"],
                "g03b_receipt_identity": receipt_out["g03b_receipt_identity"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
