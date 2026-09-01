"""Freeze the blind Romanian-naturalness review for Pilot 07 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
G03C_COMMIT = "8691e0c8b77f36a8699ec75a76b33e1ca04d0407"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
G03C_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g03c-receipt-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G03C_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write_json(name: str, value: dict[str, Any]) -> None:
    (ARTIFACTS / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G03C_COMMIT, "HEAD differs from the authorized G03C commit")
    candidate_bytes = subprocess.check_output(["git", "show", f"{G03C_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    g03c = git_json(G03C_RECEIPT_PATH)
    require(hashlib.sha256(candidate_bytes).hexdigest() == g03c["candidate_raw_sha256"], "candidate bytes")
    require(g03c["g03c_verdict"] == "CANDIDATE_SHORTCUT_PASS_AND_POOL_REBALANCING_PROGRESS_PENDING_QUALITY_GATES_AND_G04B", "G03C verdict")
    require(g03c["g03c_diagnostic_identity"] == "34980657a581989c295bf4c1037f38210fe71832bb45e4a038b25d44caf5204e", "diagnostic identity")
    require(g03c["g03c_receipt_identity"] == "941d3108ff6c515eb556bca77b063a3c58a5b31b9ab18800a4b10915d87ab705", "receipt identity")
    require(candidate_bytes.endswith(b"\n") and not candidate_bytes.startswith(b"\xef\xbb\xbf"), "candidate encoding")
    candidate = candidate_bytes.decode("utf-8").rstrip("\n")

    authority_matrix = {
        key: False
        for key in (
            "voice_review",
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
        "schema_name": "batch2-development-pilot07-candidate01-g04a-romanian-naturalness-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g03c["candidate_identity"],
        "candidate_raw_sha256": g03c["candidate_raw_sha256"],
        "g03c_commit": G03C_COMMIT,
        "g03c_receipt_identity": g03c["g03c_receipt_identity"],
        "g03c_diagnostic_identity": g03c["g03c_diagnostic_identity"],
        "review_mode": "BLIND_ROMANIAN_SURFACE_ONLY",
        "evaluator_visible": {
            "candidate_surface": candidate,
            "rubric": [
                "BASIC_GRAMMATICALITY",
                "IDIOMATIC_WORD_ORDER_AND_REGISTER",
                "NO_CALQUE",
                "NATURAL_CREATIVE_MARKING",
                "NO_FORCED_WORDPLAY",
                "COHESION_AND_PUNCTUATION",
                "NO_INSTRUCTION_OR_GOVERNANCE_REGISTER_TRANSFER",
            ],
        },
        "evaluator_inaccessible": [
            "sealed assignment mapping",
            "mechanism identity, name, or ordinal",
            "constructor packet and prompt",
            "G03 and G03B mechanism judgments",
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
                "finding": "Cele două enunțuri sunt corecte gramatical; acordurile, timpurile și referințele pronominale sunt clare.",
            },
            "idiomatic_word_order_and_register": {
                "verdict": "PASS_WITH_RESERVATION",
                "finding": "Ordinea este firească pentru un registru procedural-comic. Repetarea substantivelor «rubrică», «analiză» și «înscriere» produce o ușoară densitate nominală, dar rămâne inteligibilă și motivată local.",
            },
            "no_calque": {
                "verdict": "PASS",
                "finding": "Nu apare un calc sintactic identificabil sau o ordine străină limbii române.",
            },
            "natural_creative_marking": {
                "verdict": "PASS_WITH_RESERVATION",
                "finding": "«Într-o continuare imaginară» marchează clar și corect planul nonfactual; formula este ușor editorială, însă nu sună ca o avertizare de conformitate și nu rupe lectura.",
            },
            "no_forced_wordplay": {
                "verdict": "PASS",
                "finding": "Comparația finală dintre lungimea raportului și verificare este deliberat incongruentă, dar formulată firesc și fără forțarea unui sens lexical.",
            },
            "cohesion_and_punctuation": {
                "verdict": "PASS",
                "finding": "Punctul și virgula, coordonarea prin «iar» și consecința introdusă prin «astfel că» fac succesiunea ușor de urmărit.",
            },
            "instruction_or_governance_register_transfer": {
                "verdict": "PASS",
                "finding": "Textul nu conține cerințe, etichete, metadate ori formule de audit; registrul procedural provine din situația relatată, nu din instrucțiuni de construcție.",
            },
            "overall_naturalness": {
                "verdict": "PASS",
                "finding": "Textul este idiomatic, coerent și oralizabil. Densitatea nominală și marcajul ușor editorial sunt rezerve minore, nemateriale.",
            },
        },
        "g04a_verdict": "ROMANIAN_NATURALNESS_PASS",
        "reservations": [
            "MINOR_PROCEDURAL_NOMINAL_REPETITION_NONMATERIAL",
            "MINOR_EDITORIAL_CREATIVE_MARKER_NONMATERIAL",
        ],
        "candidate_bytes_modified": False,
        "candidate_repair_attempted": False,
        "disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_VOICE_REVIEW_ONLY",
        "authority_matrix": authority_matrix,
    }
    review = {
        **core,
        "g04a_review_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G04A_NATURALNESS_REVIEW_V1", core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot07-candidate01-g04a-romanian-naturalness-receipt-v1",
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
        "authority_matrix": authority_matrix,
    }
    receipt = {
        **receipt_core,
        "g04a_receipt_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G04A_NATURALNESS_RECEIPT_V1", receipt_core),
    }
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-g04a-naturalness-review-v1.json", review)
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-g04a-naturalness-receipt-v1.json", receipt)
    print(json.dumps({
        "g04a_verdict": core["g04a_verdict"],
        "g04a_review_identity": review["g04a_review_identity"],
        "g04a_receipt_identity": receipt["g04a_receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
