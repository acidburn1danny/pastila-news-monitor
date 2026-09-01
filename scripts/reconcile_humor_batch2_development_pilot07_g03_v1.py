"""Reveal Pilot 07 mapping only after blind-pass freeze and reconcile G03."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BLIND_COMMIT = "5f63f7d095511981d9813965664690289d9d7bf9"
MAPPING_COMMIT = "b63a4c0b321f15bf5af89fa44ed46a8c088f2f3b"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(commit, path):
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def write(name, value):
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main():
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != BLIND_COMMIT:
        raise SystemExit("HEAD")
    open_pass = load(BLIND_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot07-g03-open-blind-pass-v1.json")
    contrast = load(BLIND_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot07-g03-contrast-blind-pass-v1.json")
    for value, namespace in ((open_pass, "B2_PILOT07_G03_OPEN_BLIND_PASS_V1"), (contrast, "B2_PILOT07_G03_CONTRAST_BLIND_PASS_V1")):
        core = dict(value); identity = core.pop("blind_pass_identity")
        if seal(namespace, core) != identity or value["sealed_mapping_accessed"] or value["reconciliation_performed"]:
            raise SystemExit("blind-pass integrity")
    mapping = load(MAPPING_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot07-sealed-rebalancing-assignment-v3.json")
    core = dict(mapping); mapping_id = core.pop("sealed_assignment_identity")
    if seal("B2_DEVELOPMENT_PILOT07_SEALED_REBALANCING_ASSIGNMENT_V3", core) != mapping_id:
        raise SystemExit("mapping seal")
    target = mapping["target_mapping"]
    if target["mechanism_name"] != "Absurd Logical Extension":
        raise SystemExit("target")
    open_alignment = (open_pass["primary_role"] == "DOMINANT" and open_pass["confidence"] == "HIGH"
                      and "BUCLA_AUTOREFERENTIALA_ABSURDA" in open_pass["primary_mechanism_description"]
                      and "RECURSIA_COMPLETA" in open_pass["structural_rationale"])
    closed_alignment = (contrast["primary_choice"] == "ABSURD_LOGICAL_EXTENSION"
                        and contrast["primary_role"] == "DOMINANT" and contrast["confidence"] == "HIGH")
    if not open_alignment or not closed_alignment:
        raise SystemExit("recovery mismatch")
    classification = "TARGET_RECOVERED_DOMINANT"
    rec_core = {
        "schema_name": "batch2-development-pilot07-g03-reconciliation-v1", "schema_version": "1.0.0",
        "candidate_identity": open_pass["candidate_identity"], "candidate_raw_sha256": open_pass["candidate_raw_sha256"],
        "blind_pass_freeze_commit": BLIND_COMMIT, "assignment_commit": MAPPING_COMMIT,
        "open_pass_identity": open_pass["blind_pass_identity"], "contrast_pass_identity": contrast["blind_pass_identity"],
        "sealed_assignment_identity": mapping_id, "mapping_revealed_after_both_passes_frozen": True,
        "sealed_target": target, "open_pass_alignment": "TARGET_OPERATION_RECOVERED_DOMINANT_IN_NEUTRAL_DESCRIPTION",
        "contrast_pass_alignment": "EXACT_TARGET_RECOVERED_DOMINANT", "substantive_disagreement": False,
        "target_dominant_recovery_established": True, "reconciliation_classification": classification,
        "candidate_modified": False, "candidate_reinterpreted_or_repaired": False,
    }
    reconciliation = {**rec_core, "reconciliation_identity": seal("B2_DEVELOPMENT_PILOT07_G03_RECONCILIATION_V1", rec_core)}
    receipt_core = {
        "schema_name": "batch2-development-pilot07-g03-receipt-v1", "schema_version": "1.0.0",
        "candidate_identity": open_pass["candidate_identity"], "candidate_raw_sha256": open_pass["candidate_raw_sha256"],
        "creative_premise_family_id": "39db5384af4870785ef54b076c73afed4be48a82fedd5a899f576f97d0dac558",
        "g02c_conformance_receipt_identity": "1b445cef4b9bf16a46fc3e74c5ee2d115f1f681fa6916d0dc88ce20c3d71eeb8",
        "g03_validity_status": "VALID_BLIND_REVIEW",
        "open_recovery": {"primary": open_pass["primary_mechanism_description"], "role": open_pass["primary_role"], "confidence": open_pass["confidence"], "supporting": open_pass["supporting_mechanisms"]},
        "contrast_recovery": {"primary": contrast["primary_choice"], "role": contrast["primary_role"], "confidence": contrast["confidence"], "supporting": contrast["supporting_choices"]},
        "shortcut_findings": {"open": open_pass["shortcut_assessment"], "contrast": contrast["shortcut_assessment"]},
        "reconciliation_identity": reconciliation["reconciliation_identity"], "reconciliation_classification": classification,
        "target_dominant_recovery_established": True, "candidate_modified": False,
        "g03b_performed": False, "g03c_performed": False, "romanian_naturalness_review_performed": False,
        "voice_review_performed": False, "owner_review_performed": False,
        "authority_matrix": {key: False for key in ("g03b", "g03c", "g04a", "g04b_pool_certification", "voice_review", "owner_review", "repair", "rewrite", "regeneration", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**receipt_core, "g03_receipt_identity": seal("B2_DEVELOPMENT_PILOT07_G03_RECEIPT_V1", receipt_core)}
    write("humor-mechanics-batch2-development-pilot07-g03-reconciliation-v1.json", reconciliation)
    write("humor-mechanics-batch2-development-pilot07-g03-receipt-v1.json", receipt)
    print(json.dumps({"g03_validity_status": receipt["g03_validity_status"], "open_primary": open_pass["primary_mechanism_description"], "contrast_primary": contrast["primary_choice"], "reconciliation_classification": classification, "reconciliation_identity": reconciliation["reconciliation_identity"], "g03_receipt_identity": receipt["g03_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
