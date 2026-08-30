"""Freeze blind G03 choice, pass B, isolation, and reconciliation artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write_once(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit(f"already frozen: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    pass_a_path = ART / "humor-mechanics-batch2-development-pilot01-candidate01-g03-pass-a-v1.json"
    pass_a = json.loads(pass_a_path.read_text(encoding="utf-8"))
    mapping_path = ART / "humor-mechanics-batch2-development-pilot01-sealed-assignment-mapping-v1.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert pass_a["pass_a_identity"] == "f42aaa19b452af5110e264ad12f1974dabb355861d3d5a7641fb969824f28512"
    choices = [
        {"display_ordinal": 1, "choice": "NONE", "definition": "No listed mechanism adequately describes the dominant operation."},
        {"display_ordinal": 2, "choice": "ESCALATION", "definition": "Successive elements increase intensity, stakes, or comic force."},
        {"display_ordinal": 3, "choice": "ABSURD_ALTERNATIVES_WITHOUT_SELECTION", "definition": "Multiple fictional absurd possibilities are offered without choosing or privileging one."},
        {"display_ordinal": 4, "choice": "AMBIGUOUS", "definition": "The evidence does not support a unique choice among the listed mechanisms."},
        {"display_ordinal": 5, "choice": "HYPERBOLE", "definition": "Deliberate exaggeration enlarges magnitude or degree for comic effect."},
        {"display_ordinal": 6, "choice": "ABSURD_LOGICAL_EXTENSION", "definition": "A premise is extended through an internally logical chain to an absurd implication."},
    ]
    choice_core = {
        "schema_name": "batch2-development-pilot01-g03-choice-set-v1", "schema_version": "1.0.0",
        "candidate_identity": pass_a["candidate_identity"],
        "shuffle_derivation": "SHA256(PILOT01_G03_CHOICE_SET_V1 || candidate_identity)",
        "canonical_member_set_sha256": "3a06750f633d8bfae9099857ba1645d7ea292c4a908c5ec00c9130df7377f730",
        "displayed_order_sha256": "ae7d02551ea2668cabc75f5a0593d072c2e0c12a005d83dac04f80cfe7e5d809",
        "choices": choices, "target_status_disclosed": False,
    }
    choice = {**choice_core, "choice_set_identity": seal("B2_DEVELOPMENT_PILOT01_G03_CHOICE_SET_V1", choice_core)}
    pass_b_result = {
        "primary_choice": "ABSURD_LOGICAL_EXTENSION", "primary_role": "DOMINANT",
        "supporting_choices": ["ESCALATION"], "confidence": "HIGH",
        "defining_operation": "Premisa verificărilor succesive este continuată ca un lanț birocratic coerent intern: regula «intră în tură», iar verificarea de la 17:00 îi «închide pontajul», producând implicația absurdă că regula sau mobilierul are program de muncă.",
        "structural_dependency": "Efectul depinde de relația cauzal-temporală dintre intrarea în tură și închiderea pontajului la verificarea ulterioară; fără acest lanț, rămâne doar o personificare izolată.",
        "comparisons": {
            "NONE": "Există un mecanism listat care descrie precis operația dominantă.",
            "ESCALATION": "Succesiunea amplifică ușor comicul, dar funcția principală este deducția absurdă, nu simpla creștere de intensitate.",
            "ABSURD_ALTERNATIVES_WITHOUT_SELECTION": "Textul dezvoltă o singură continuare imaginară, nu oferă mai multe alternative nealese.",
            "AMBIGUOUS": "Lanțul explicit și coerent intern diferențiază suficient extensia logică absurdă de mecanismele concurente.",
            "HYPERBOLE": "Nu este mărită o magnitudine sau un grad; absurdul provine din aplicarea logicii pontajului unor entități care nu muncesc.",
        },
        "shortcut_dependence": {"lexical": "NON_MATERIAL", "punctuation": "NON_MATERIAL", "formatting": "NON_MATERIAL", "source_shape": "NON_MATERIAL", "template": "NON_MATERIAL", "explanation": "Clasificarea rezultă din structura semantică și temporal-cauzală a continuării, nu din indicii de suprafață."},
    }
    pass_b_core = {
        "schema_name": "batch2-development-pilot01-g03-contrast-pass-b-v1", "schema_version": "1.0.0",
        "candidate_identity": pass_a["candidate_identity"], "g02_identity": pass_a["g02_identity"],
        "choice_set_identity": choice["choice_set_identity"], "pass": "B_SHUFFLED_CONTRAST",
        "sealed_mapping_exposed": False, "pass_a_exposed": False, "repository_access": False,
        "result": pass_b_result,
    }
    pass_b = {**pass_b_core, "pass_b_identity": seal("B2_DEVELOPMENT_PILOT01_G03_PASS_B_V1", pass_b_core)}
    isolation_core = {
        "schema_name": "batch2-development-pilot01-g03-blind-isolation-v1", "schema_version": "1.0.0",
        "candidate_identity": pass_a["candidate_identity"], "pass_a_identity": pass_a["pass_a_identity"],
        "pass_b_identity": pass_b["pass_b_identity"], "choice_set_identity": choice["choice_set_identity"],
        "pass_a_target_accesses": 0, "pass_b_target_accesses": 0,
        "pass_a_other_pass_accesses": 0, "pass_b_other_pass_accesses": 0,
        "assignment_constructor_owner_history_blind_material_exposure": False,
        "evaluators_noncommunicating": True, "passes_frozen_before_reconciliation": True,
        "verdict": "PASS",
    }
    isolation = {**isolation_core, "isolation_identity": seal("B2_DEVELOPMENT_PILOT01_G03_BLIND_ISOLATION_V1", isolation_core)}
    assert mapping["target_mapping"]["mechanism_id"] == "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION"
    reconciliation_core = {
        "schema_name": "batch2-development-pilot01-g03-reconciliation-v1", "schema_version": "1.0.0",
        "candidate_identity": pass_a["candidate_identity"], "sealed_assignment_identity": mapping["sealed_assignment_identity"],
        "target_mechanism": mapping["target_mapping"]["mechanism_id"],
        "pass_a_primary": pass_a["result"]["primary_mechanism"], "pass_a_target_recovered": False,
        "pass_b_primary": pass_b_result["primary_choice"], "pass_b_target_recovered": True,
        "pass_agreement": "DISAGREE_ON_DOMINANT_MECHANISM",
        "classification": "AMBIGUOUS_MECHANISM",
        "reason": "Open recovery found PERSONIFICATION dominant while the closed contrast pass selected the target. A target recovered only after closed-set exposure cannot override the valid open-pass disagreement.",
        "passes_modified_after_reveal": False,
    }
    reconciliation = {**reconciliation_core, "reconciliation_identity": seal("B2_DEVELOPMENT_PILOT01_G03_RECONCILIATION_V1", reconciliation_core)}
    g03_core = {
        "schema_name": "batch2-development-pilot01-g03-receipt-v1", "schema_version": "1.0.0",
        "candidate_identity": pass_a["candidate_identity"], "candidate_raw_sha256": "2f848e2bc9d87b113df95996a4d49d48fbe4334d6c204ef707664158e23caf9d",
        "g02_identity": pass_a["g02_identity"], "pass_a_identity": pass_a["pass_a_identity"],
        "pass_b_identity": pass_b["pass_b_identity"], "choice_set_identity": choice["choice_set_identity"],
        "isolation_identity": isolation["isolation_identity"], "reconciliation_identity": reconciliation["reconciliation_identity"],
        "g03_validity": "VALID_BLIND_REVIEW", "reconciliation_classification": "AMBIGUOUS_MECHANISM",
        "candidate_advanced": False, "candidate_repaired_or_reinterpreted": False,
        "next_gate_eligible": False,
        "authority_matrix": {key: False for key in ("g03b_minimal_intervention", "g03c_shortcut_pool_audit", "romanian_naturalness_review", "voice_review", "owner_review", "repair", "regeneration", "selection", "training", "runtime_integration", "production_routing")},
    }
    g03 = {**g03_core, "g03_receipt_identity": seal("B2_DEVELOPMENT_PILOT01_G03_RECEIPT_V1", g03_core)}
    write_once("humor-mechanics-batch2-development-pilot01-candidate01-g03-choice-set-v1.json", choice)
    write_once("humor-mechanics-batch2-development-pilot01-candidate01-g03-pass-b-v1.json", pass_b)
    write_once("humor-mechanics-batch2-development-pilot01-candidate01-g03-blind-isolation-v1.json", isolation)
    write_once("humor-mechanics-batch2-development-pilot01-candidate01-g03-reconciliation-v1.json", reconciliation)
    write_once("humor-mechanics-batch2-development-pilot01-candidate01-g03-receipt-v1.json", g03)
    print(json.dumps({"g03_receipt_identity": g03["g03_receipt_identity"], "classification": g03["reconciliation_classification"]}, sort_keys=True))


if __name__ == "__main__":
    main()
