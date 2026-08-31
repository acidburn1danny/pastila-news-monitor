"""Freeze the independently completed Pilot 06 blind G03 passes before reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "54e773a8dac9e9be5ad3ca352a871f5284bbbd6f"
CANDIDATE = "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-v1.txt"
G02C = "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-g02c-review-v2.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name: str, value: Any) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    candidate = subprocess.check_output(["git", "show", f"{COMMIT}:{CANDIDATE}"], cwd=ROOT)
    g02c = json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{G02C}"], cwd=ROOT))
    if hashlib.sha256(candidate).hexdigest() != "e00b1b83507ece1808445a3f6cfd07286ee20eecc6f4208d9aa4940ab2fbc1a9":
        raise SystemExit("candidate")
    if g02c["g02c_verdict"] != "PASS" or g02c["g02c_review_identity"] != "9c00bdaf3273b24548c12e176f410f3167c8ae35e6bdf2abfdc2843d0ee093d2":
        raise SystemExit("G02C")
    common = {"candidate_identity": "61b4c89e4ec65ac211debc034ed35f47f79a2757551266a90fadf5acde270773",
              "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(), "g02c_review_identity": g02c["g02c_review_identity"],
              "candidate_modified": False, "sealed_mapping_accessed": False, "reconciliation_performed": False}
    open_core = {
        "schema_name": "batch2-development-pilot06-g03-open-blind-pass-v1", "schema_version": "1.0.0", **common,
        "review_mode": "OPEN_RECOVERY_NO_CHOICE_LABELS", "reviewer_independence": "INDEPENDENT_SURFACE_ONLY",
        "primary_mechanism_description": "EXTINDERE_CAUZALA_ABSURDA_PRIN_LITERALIZAREA_INSCRIERII_UNEI_DATE",
        "primary_role": "DOMINANT", "confidence": "HIGH",
        "supporting_mechanisms": ["REIFICAREA_DATEI_CA_OBIECT_TRANSFERABIL_SAU_ABSORBABIL",
                                  "INCONGRUITATE_PROCEDURA_ADMINISTRATIVA_VS_CONSECINTA_IMPOSIBILA",
                                  "METAFORA_ANIMATA_A_REGISTRULUI_CARE_ABSOARBE_DATA"],
        "structural_rationale": "RELATIA_REALISTA_DE_EVIDENTA_ESTE_LITERALIZATA_CA_TRANSFER_FIZIC_IAR_DISPARITIA_ZILEI_ESTE_DERIVATA_CA_URMARE_IMPOSIBILA",
        "shortcut_assessment": {"overall": "LOW", "lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL",
                                "source_order": "FACILITATES_RECOVERY_BUT_SEMANTIC_RELATION_REQUIRED",
                                "template": "LOW_BUT_RECOGNIZABLE_ADMINISTRATIVE_FACT_TO_IMAGINARY_LITERAL_CONSEQUENCE"},
    }
    open_pass = {**open_core, "blind_pass_identity": seal("B2_PILOT06_G03_OPEN_BLIND_PASS_V1", open_core)}
    contrast_core = {
        "schema_name": "batch2-development-pilot06-g03-contrast-blind-pass-v1", "schema_version": "1.0.0", **common,
        "review_mode": "SHUFFLED_CLOSED_CHOICE", "reviewer_independence": "INDEPENDENT_SURFACE_ONLY",
        "shuffled_choices": ["HYPERBOLE", "NONE", "ABSURD_LOGICAL_EXTENSION", "ESCALATION", "MISDIRECTION", "AMBIGUOUS"],
        "primary_choice": "MISDIRECTION", "primary_role": "DOMINANT", "confidence": "HIGH",
        "supporting_choices": ["ABSURD_LOGICAL_EXTENSION"],
        "structural_rationale": "ABSURD_INITIAL_EXPLANATION_PRECEDES_A_BANAL_ADMINISTRATIVE_DISCLOSURE_THAT_RETROSPECTIVELY_REORIENTS_THE_READING",
        "alternative_findings": {"HYPERBOLE": "NOT_MAGNITUDE_AMPLIFICATION", "NONE": "CLEAR_REORIENTATION_PRESENT",
                                 "ABSURD_LOGICAL_EXTENSION": "PRESENT_AS_SUPPORTING_LOCAL_INFERENCE_NOT_WHOLE_SURFACE_DOMINANT",
                                 "ESCALATION": "NO_INCREASE_IN_INTENSITY_OR_STAKES", "AMBIGUOUS": "MISDIRECTION_JUDGED_MORE_SPECIFIC"},
        "shortcut_assessment": {"lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL", "template": "NON_MATERIAL"},
    }
    contrast_pass = {**contrast_core, "blind_pass_identity": seal("B2_PILOT06_G03_CONTRAST_BLIND_PASS_V1", contrast_core)}
    write("humor-mechanics-batch2-development-pilot06-g03-open-blind-pass-v1.json", open_pass)
    write("humor-mechanics-batch2-development-pilot06-g03-contrast-blind-pass-v1.json", contrast_pass)
    print(json.dumps({"open_pass_identity": open_pass["blind_pass_identity"],
                      "contrast_pass_identity": contrast_pass["blind_pass_identity"],
                      "sealed_mapping_accessed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
