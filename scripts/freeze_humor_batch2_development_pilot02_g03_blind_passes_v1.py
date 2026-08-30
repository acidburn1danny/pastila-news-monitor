"""Freeze the two completed Pilot 02 blind G03 passes before reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02C_COMMIT = "015ceb5fc41d3f97c6884995394e31ad4e6b947a"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name: str, value: Any) -> None:
    (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != G02C_COMMIT:
        raise SystemExit("HEAD differs from G02C commit")
    candidate = subprocess.check_output(["git", "show", f"{G02C_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    if hashlib.sha256(candidate).hexdigest() != "5c50ca8e4ae5ea32301c02ec8ea4104482bbc9c8e3c7e8314516d09aeb591fd3":
        raise SystemExit("candidate hash")
    choice_members = [
        "Personification", "NONE", "Hyperbole", "Absurd Logical Extension", "AMBIGUOUS",
        "Frame Transfer", "Escalation", "Absurd Alternatives Without Selection",
    ]
    choice_core = {
        "schema_name": "batch2-development-pilot02-g03-choice-set-v1",
        "schema_version": "1.0.0",
        "candidate_identity": "4cc6bceef84e29d07e19d60dbbb1992b33fcb8af67373647f5fb8fedfce1d98c",
        "displayed_order": choice_members,
        "displayed_order_sha256": hashlib.sha256(canonical(choice_members)).hexdigest(),
        "member_set_sha256": hashlib.sha256(canonical(sorted(choice_members))).hexdigest(),
        "contains_none": True,
        "contains_ambiguous": True,
        "shown_to_open_pass": False,
        "shown_to_contrast_pass": True,
        "mapping_revealed": False,
    }
    choice = {**choice_core, "choice_set_identity": seal("B2_DEVELOPMENT_PILOT02_G03_CHOICE_SET_V1", choice_core)}
    open_result = {
        "primary_mechanism": "paradox temporal autoanulant",
        "primary_role": "DOMINANT",
        "supporting_mechanisms": ["cauzalitate circulară", "escaladare logică absurdă", "literalizarea unei condiții procedurale"],
        "confidence": "HIGH",
        "defining_surface_operation": "Absența rezultatului la momentul final este transformată într-o cauză care anulează mai întâi finalul și apoi chiar existența acelui moment, retrăgând retroactiv cadrul premisei.",
        "structural_dependency": "Efectul depinde de bucla dintre stabilirea câștigătorului și încheierea testului: fiecare este făcută condiție pentru cealaltă, iar eșecul uneia elimină punctul temporal în care eșecul fusese constatat.",
        "strongest_alternative": "Catch-22 procedural",
        "alternative_comparison": "Există o imposibilitate procedurală circulară, dar operația mai specifică și dominantă este autoanularea temporală: nu doar că testul nu poate fi încheiat, ci dispare momentul final invocat inițial.",
        "shortcut_dependence": {
            "lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL", "formatting": "NON_MATERIAL",
            "source_shape": "NON_MATERIAL", "template": "NON_MATERIAL",
            "explanation": "Mecanismul rezultă din relațiile cauzale și temporale dintre propoziții; parafrazarea, schimbarea punctuației, a formatului sau a formei-sursă nu l-ar elimina cât timp bucla autoanulantă rămâne intactă.",
        },
    }
    open_core = {
        "schema_name": "batch2-development-pilot02-g03-open-recovery-pass-v1", "schema_version": "1.0.0",
        "candidate_identity": choice_core["candidate_identity"], "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
        "evaluator_identity": "INDEPENDENT_BLIND_EVALUATOR_PILOT02_OPEN",
        "visible_inputs": ["IMMUTABLE_CANDIDATE_SURFACE_ONLY"],
        "choice_set_visible": False, "mapping_visible": False, "result": open_result,
    }
    open_pass = {**open_core, "pass_identity": seal("B2_DEVELOPMENT_PILOT02_G03_OPEN_PASS_V1", open_core)}
    contrast_result = {
        "primary_choice": "Absurd Logical Extension", "primary_role": "DOMINANT", "supporting_choices": [], "confidence": "HIGH",
        "defining_operation": "Premisa că nu există încă un câștigător este prelungită într-un lanț cauzal inteligibil, dar absurd: absența lui suspendă încheierea testului, iar imposibilitatea încheierii elimină însuși momentul stabilirii câștigătorului.",
        "structural_dependency": "Efectul depinde de succesiunea inferențială premisă–consecință–consecință absurdă; fără această extensie logică, suprafața rămâne doar o constatare administrativă.",
        "comparisons": {
            "Personification": "Testul și momentul nu primesc intenție, emoție, voce sau rol uman.",
            "NONE": "Există o operație dominantă clară din set: dezvoltarea inferențială a premisei până la o consecință absurdă.",
            "Hyperbole": "Comicul nu provine din mărirea deliberată a unei magnitudini sau a unui grad.",
            "AMBIGUOUS": "Lanțul cauzal absurd identifică mai precis mecanismul decât oricare alternativă concurentă.",
            "Frame Transfer": "Nu este importat un sistem coerent de relații sau convenții dintr-un domeniu separat.",
            "Escalation": "Pașii avansează logic, dar nu urmăresc în primul rând creșterea intensității ori a mizelor.",
            "Absurd Alternatives Without Selection": "Este prezentat un singur traseu consecvențial, nu mai multe posibilități absurde lăsate neselectate.",
        },
        "shortcut_dependence": {
            "lexical": {"value": "NON_MATERIAL", "explanation": "Alegerea nu depinde de un cuvânt-semnal, ci de relațiile cauzale dintre propoziții."},
            "punctuation": {"value": "NON_MATERIAL", "explanation": "Punctuația doar delimitează lanțul și nu determină mecanismul."},
            "formatting": {"value": "NON_MATERIAL", "explanation": "Mecanismul persistă indiferent de prezentarea tipografică."},
            "source_shape": {"value": "NON_MATERIAL", "explanation": "Clasificarea rezultă din operația semantică internă, nu din forma sau proveniența suprafeței."},
            "template": {"value": "NON_MATERIAL", "explanation": "Nu este necesară recunoașterea unui șablon; lanțul inferențial este explicit în text."},
        },
    }
    contrast_core = {
        "schema_name": "batch2-development-pilot02-g03-contrast-choice-pass-v1", "schema_version": "1.0.0",
        "candidate_identity": choice_core["candidate_identity"], "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
        "evaluator_identity": "INDEPENDENT_BLIND_EVALUATOR_PILOT02_CONTRAST",
        "visible_inputs": ["IMMUTABLE_CANDIDATE_SURFACE", "SHUFFLED_CLOSED_CHOICE_SET"],
        "choice_set_identity": choice["choice_set_identity"], "mapping_visible": False, "result": contrast_result,
    }
    contrast_pass = {**contrast_core, "pass_identity": seal("B2_DEVELOPMENT_PILOT02_G03_CONTRAST_PASS_V1", contrast_core)}
    isolation_core = {
        "schema_name": "batch2-development-pilot02-g03-blind-isolation-v1", "schema_version": "1.0.0",
        "candidate_identity": choice_core["candidate_identity"], "g02c_commit": G02C_COMMIT,
        "open_pass_identity": open_pass["pass_identity"], "contrast_pass_identity": contrast_pass["pass_identity"],
        "independent_evaluators": True, "inter_evaluator_communication": False,
        "sealed_mapping_access": False, "constructor_packet_access": False, "obligation_identity_access": False,
        "g02c_reasoning_access": False, "owner_history_access": False, "blind_evaluation_material_access": False,
        "candidate_modified": False, "mapping_revealed": False, "status": "BLIND_PASSES_FROZEN_AWAITING_RECONCILIATION",
    }
    isolation = {**isolation_core, "isolation_identity": seal("B2_DEVELOPMENT_PILOT02_G03_BLIND_ISOLATION_V1", isolation_core)}
    write("humor-mechanics-batch2-development-pilot02-candidate01-g03-choice-set-v1.json", choice)
    write("humor-mechanics-batch2-development-pilot02-candidate01-g03-pass-a-v1.json", open_pass)
    write("humor-mechanics-batch2-development-pilot02-candidate01-g03-pass-b-v1.json", contrast_pass)
    write("humor-mechanics-batch2-development-pilot02-candidate01-g03-blind-isolation-v1.json", isolation)
    print(json.dumps({"status": isolation["status"], "choice_set_identity": choice["choice_set_identity"],
                      "open_pass_identity": open_pass["pass_identity"], "contrast_pass_identity": contrast_pass["pass_identity"],
                      "isolation_identity": isolation["isolation_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
