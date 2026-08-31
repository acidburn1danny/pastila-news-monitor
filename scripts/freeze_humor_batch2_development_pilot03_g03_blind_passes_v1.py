"""Freeze Pilot 03's two blind G03 passes before mapping reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02C_COMMIT = "bb16e85bb6d28de972e8af9cdc7f54320f379e74"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-v1.txt"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name: str, value: Any) -> None:
    (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != G02C_COMMIT:
        raise SystemExit("HEAD differs from G02C commit")
    candidate = subprocess.check_output(["git", "show", f"{G02C_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    if hashlib.sha256(candidate).hexdigest() != "86f058253be11227bf40a0de4842bf79ae7458b2a89f11c8fca033477e0a626d":
        raise SystemExit("candidate hash")
    candidate_id = "b4555cc43bf16a466734aed46e93baa83bd9bc37d52d3826976be3370ccef72d"
    members = ["Frame Transfer", "AMBIGUOUS", "Comic Reclassification", "Personification",
               "Absurd Logical Extension", "NONE", "Literalization", "Escalation"]
    choice_core = {"schema_name": "batch2-development-pilot03-g03-choice-set-v1", "schema_version": "1.0.0",
                   "candidate_identity": candidate_id, "displayed_order": members,
                   "displayed_order_sha256": hashlib.sha256(canonical(members)).hexdigest(),
                   "member_set_sha256": hashlib.sha256(canonical(sorted(members))).hexdigest(),
                   "contains_none": True, "contains_ambiguous": True,
                   "shown_to_open_pass": False, "shown_to_contrast_pass": True, "mapping_revealed": False}
    choice = {**choice_core, "choice_set_identity": seal("B2_DEVELOPMENT_PILOT03_G03_CHOICE_SET_V1", choice_core)}
    open_result = {
        "primary_mechanism": "lanț inferențial absurd cu reîncadrare finală",
        "primary_role": "DOMINANT",
        "supporting_mechanisms": ["reclasificarea deschiderii ca obiect inventariabil"],
        "confidence": "HIGH",
        "defining_surface_operation": "Necunoașterea conținutului produce o listă goală; incapacitatea listei de a confirma ceva face apoi ca însăși deschiderea să devină singurul lucru inventariabil.",
        "structural_dependency": "A doua situație există numai după prima: fără lista goală nu apare lipsa confirmării, iar fără aceasta deschiderea nu este reîncadrată ca element de inventar.",
        "strongest_alternative": "reclasificare comică",
        "alternative_comparison": "Reclasificarea apare în consecința finală, dar efectul dominant cere întregul traseu premisă–consecință–consecință absurdă.",
        "shortcut_dependence": {"lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL",
                                "formatting": "NON_MATERIAL", "source_shape": "NON_MATERIAL", "template": "NON_MATERIAL",
                                "explanation": "Clasificarea rezultă din dependența semantică dintre cele două situații, nu dintr-un cuvânt, semn de punctuație ori format."},
    }
    open_core = {"schema_name": "batch2-development-pilot03-g03-open-recovery-pass-v1", "schema_version": "1.0.0",
                 "candidate_identity": candidate_id, "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
                 "evaluator_identity": "BLIND_REVIEW_CHANNEL_PILOT03_OPEN",
                 "visible_inputs": ["IMMUTABLE_CANDIDATE_SURFACE_ONLY"], "choice_set_visible": False,
                 "mapping_visible": False, "result": open_result}
    open_pass = {**open_core, "pass_identity": seal("B2_DEVELOPMENT_PILOT03_G03_OPEN_PASS_V1", open_core)}
    comparisons = {
        "Frame Transfer": "Nu este importat un cadru relațional complet din alt domeniu; inventarul aparține deja situației create.",
        "AMBIGUOUS": "Lanțul dependent identifică o operație dominantă mai precis decât alternativele concurente.",
        "Comic Reclassification": "Deschiderea este reclasificată în final, dar numai ca rezultat al celor două inferențe dependente.",
        "Personification": "Coletul, lista și deschiderea nu primesc emoție, intenție, voce sau rol uman.",
        "NONE": "Suprafața conține o operație structurală clară, nu doar o constatare factuală.",
        "Literalization": "O noțiune figurată nu este realizată fizic; schimbarea este inferențială și categorială.",
        "Escalation": "Consecințele avansează, dar efectul nu depinde în primul rând de creșterea intensității sau a mizei.",
    }
    contrast_result = {
        "primary_choice": "Absurd Logical Extension", "primary_role": "DOMINANT",
        "supporting_choices": ["Comic Reclassification"], "confidence": "HIGH",
        "defining_operation": "Premisa despre conținutul necunoscut este prelungită în două consecințe inteligibile local: lista rămâne goală, apoi deschiderea însăși devine obiectul inventariabil.",
        "structural_dependency": "Eliminarea primei consecințe rupe motivul pentru a doua; rezultatul absurd depinde de succesiunea inferențială completă.",
        "comparisons": comparisons,
        "shortcut_dependence": {key: {"value": "NON_MATERIAL", "explanation": "Alegerea depinde de relațiile semantice și persistă la parafrazare."}
                                for key in ("lexical", "punctuation", "formatting", "source_shape", "template")},
    }
    contrast_core = {"schema_name": "batch2-development-pilot03-g03-contrast-choice-pass-v1", "schema_version": "1.0.0",
                     "candidate_identity": candidate_id, "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
                     "evaluator_identity": "BLIND_REVIEW_CHANNEL_PILOT03_CONTRAST",
                     "visible_inputs": ["IMMUTABLE_CANDIDATE_SURFACE", "SHUFFLED_CLOSED_CHOICE_SET"],
                     "choice_set_identity": choice["choice_set_identity"], "mapping_visible": False, "result": contrast_result}
    contrast = {**contrast_core, "pass_identity": seal("B2_DEVELOPMENT_PILOT03_G03_CONTRAST_PASS_V1", contrast_core)}
    isolation_core = {"schema_name": "batch2-development-pilot03-g03-blind-isolation-v1", "schema_version": "1.0.0",
                      "candidate_identity": candidate_id, "g02c_commit": G02C_COMMIT,
                      "open_pass_identity": open_pass["pass_identity"], "contrast_pass_identity": contrast["pass_identity"],
                      "review_channels_separated": True, "cross_pass_result_access_before_freeze": False,
                      "sealed_mapping_access": False, "constructor_packet_access": False, "obligation_identity_access": False,
                      "g02c_reasoning_access": False, "owner_history_access": False, "blind_evaluation_material_access": False,
                      "candidate_modified": False, "mapping_revealed": False,
                      "status": "BLIND_PASSES_FROZEN_AWAITING_RECONCILIATION"}
    isolation = {**isolation_core, "isolation_identity": seal("B2_DEVELOPMENT_PILOT03_G03_BLIND_ISOLATION_V1", isolation_core)}
    write("humor-mechanics-batch2-development-pilot03-candidate01-g03-choice-set-v1.json", choice)
    write("humor-mechanics-batch2-development-pilot03-candidate01-g03-pass-a-v1.json", open_pass)
    write("humor-mechanics-batch2-development-pilot03-candidate01-g03-pass-b-v1.json", contrast)
    write("humor-mechanics-batch2-development-pilot03-candidate01-g03-blind-isolation-v1.json", isolation)
    print(json.dumps({"status": isolation["status"], "choice_set_identity": choice["choice_set_identity"],
                      "open_pass_identity": open_pass["pass_identity"], "contrast_pass_identity": contrast["pass_identity"],
                      "isolation_identity": isolation["isolation_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
