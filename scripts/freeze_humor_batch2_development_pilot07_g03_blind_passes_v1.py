"""Freeze independently completed Pilot 07 blind G03 passes before reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "2525f0f4df6b427035d4128b33b0a4235e45994d"
CANDIDATE = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
G02C = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g02c-review-v3.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name, value):
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main():
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    candidate = subprocess.check_output(["git", "show", f"{COMMIT}:{CANDIDATE}"], cwd=ROOT)
    g02c = json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{G02C}"], cwd=ROOT))
    if hashlib.sha256(candidate).hexdigest() != "769228fc99006e0f665360f28805f31d4480419095de1f1fba5794319cc1bfa8":
        raise SystemExit("candidate")
    if g02c["g02c_verdict"] != "PASS" or g02c["g02c_review_identity"] != "6b12ee5efb9a08f46495e0c19724a967ae821273ca75584392d9a87168bb9d43":
        raise SystemExit("G02C")
    common = {
        "candidate_identity": "44c76c090e226d0ef947e2fc07307fb862761e94950c4eb378b8b3d258427bc1",
        "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
        "g02c_review_identity": g02c["g02c_review_identity"],
        "candidate_modified": False,
        "sealed_mapping_accessed": False,
        "reconciliation_performed": False,
    }
    open_core = {
        "schema_name": "batch2-development-pilot07-g03-open-blind-pass-v1", "schema_version": "1.0.0", **common,
        "review_mode": "OPEN_RECOVERY_NO_CHOICE_LABELS", "reviewer_independence": "INDEPENDENT_SURFACE_ONLY",
        "primary_mechanism_description": "PROCEDURA_BIROCRATICA_PRELUNGITA_INTR_O_BUCLA_AUTOREFERENTIALA_ABSURDA",
        "primary_role": "DOMINANT", "confidence": "HIGH",
        "supporting_mechanisms": ["ESCALADARE_CUMULATIVA_PRIN_REPETAREA_CICLULUI", "INCONGRUITATE_SCOP_EFICIENT_VS_PROLIFERAREA_RAPORTULUI", "EXAGERARE_COMICA_A_LUNGIMII_RAPORTULUI"],
        "structural_rationale": "P5_STABILESTE_PROBLEMA_INSCRIERE_ANALIZA_IAR_CONTINUAREA_LEAGA_RUBRICA_ANALIZA_INSCRIERE_REPETARE_REZULTATUL_DEPINZAND_DE_RECURSIA_COMPLETA",
        "shortcut_assessment": {"overall": "LOW_CONCERN", "lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL", "formatting": "NON_MATERIAL", "source_shape": "FACILITATES_READING_BUT_FULL_DEPENDENCY_REQUIRED", "template": "LOW_REQUIRES_SPECIFIC_FIELD_ANALYSIS_ENTRY_LINKS"},
    }
    open_pass = {**open_core, "blind_pass_identity": seal("B2_PILOT07_G03_OPEN_BLIND_PASS_V1", open_core)}
    contrast_core = {
        "schema_name": "batch2-development-pilot07-g03-contrast-blind-pass-v1", "schema_version": "1.0.0", **common,
        "review_mode": "SHUFFLED_CLOSED_CHOICE", "reviewer_independence": "INDEPENDENT_SURFACE_ONLY",
        "shuffled_choices": ["ESCALATION", "NONE", "LITERALIZATION", "ABSURD_LOGICAL_EXTENSION", "AMBIGUOUS", "MISDIRECTION"],
        "primary_choice": "ABSURD_LOGICAL_EXTENSION", "primary_role": "DOMINANT", "confidence": "HIGH", "supporting_choices": [],
        "structural_rationale": "INSCRIEREA_FACTUALA_ESTE_EXTINSA_PRIN_LANTUL_RUBRICA_ANALIZA_INSCRIERE_REPETARE_PANA_LA_CONSECINTA_ABSURDA",
        "alternative_findings": {"ESCALATION": "ACUMULARE_SUBORDONATA_LANTULUI_CAUZAL", "NONE": "MECANISM_CLAR_PREZENT", "LITERALIZATION": "NICIUN_FIGURAT_NU_DEVINE_REALITATE_LITERAL_DOMINANTA", "AMBIGUOUS": "LANTUL_FAVORIZEAZA_UNIC_ALEGEREA", "MISDIRECTION": "FAPTUL_PRECEDE_CONTINUAREA_FARA_DEZVALUIRE_INTARZIATA"},
        "shortcut_assessment": {"lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL", "template": "NON_MATERIAL"},
    }
    contrast = {**contrast_core, "blind_pass_identity": seal("B2_PILOT07_G03_CONTRAST_BLIND_PASS_V1", contrast_core)}
    write("humor-mechanics-batch2-development-pilot07-g03-open-blind-pass-v1.json", open_pass)
    write("humor-mechanics-batch2-development-pilot07-g03-contrast-blind-pass-v1.json", contrast)
    print(json.dumps({"open_pass_identity": open_pass["blind_pass_identity"], "contrast_pass_identity": contrast["blind_pass_identity"], "sealed_mapping_accessed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
