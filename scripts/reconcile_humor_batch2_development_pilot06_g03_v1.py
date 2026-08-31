"""Reveal the sealed Pilot 06 mapping only after blind-pass freeze and reconcile G03."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BLIND_COMMIT = "129b32d884e99600b9c5547321b60d04599392fd"
MAPPING_COMMIT = "c2aea939a22e6e0dd3e33f05e43a8d1f0796e4d4"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def write(name: str, value: Any) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != BLIND_COMMIT:
        raise SystemExit("HEAD")
    open_pass = git_json(BLIND_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-open-blind-pass-v1.json")
    contrast = git_json(BLIND_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-contrast-blind-pass-v1.json")
    mapping = git_json(MAPPING_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot06-sealed-rebalancing-assignment-v2.json")
    if open_pass["sealed_mapping_accessed"] or contrast["sealed_mapping_accessed"]:
        raise SystemExit("blindness")
    if mapping["sealed_assignment_identity"] != "c45e19fd9416d50ac4776c1352c7afe5657501545f6405d9e2d4ba33f2b505a9":
        raise SystemExit("mapping")
    target = mapping["target_mapping"]
    open_alignment = "TARGET_OPERATION_RECOVERED_DOMINANT_IN_NEUTRAL_DESCRIPTION"
    contrast_alignment = ("TARGET_RECOVERED_SUPPORTING_NOT_DOMINANT" if target["mechanism_name"].upper().replace(" ", "_") in contrast["supporting_choices"]
                          else "TARGET_NOT_RECOVERED")
    if contrast_alignment != "TARGET_RECOVERED_SUPPORTING_NOT_DOMINANT":
        raise SystemExit("contrast reconciliation")
    reconciliation = "AMBIGUOUS_MECHANISM"
    reconciliation_core = {
        "schema_name": "batch2-development-pilot06-g03-reconciliation-v1", "schema_version": "1.0.0",
        "candidate_identity": open_pass["candidate_identity"], "candidate_raw_sha256": open_pass["candidate_raw_sha256"],
        "blind_pass_freeze_commit": BLIND_COMMIT, "open_pass_identity": open_pass["blind_pass_identity"],
        "contrast_pass_identity": contrast["blind_pass_identity"], "sealed_assignment_identity": mapping["sealed_assignment_identity"],
        "mapping_revealed_after_both_passes_frozen": True, "sealed_target": target,
        "open_pass_alignment": open_alignment, "contrast_pass_alignment": contrast_alignment,
        "dominance_disagreement": {"open_pass": "TARGET_OPERATION_DOMINANT", "contrast_pass": "MISDIRECTION_DOMINANT_TARGET_SUPPORTING",
                                  "both_confidence": "HIGH", "substantive": True},
        "target_dominant_recovery_established": False, "reconciliation_classification": reconciliation,
        "candidate_modified": False, "candidate_reinterpreted_or_repaired": False,
    }
    reconciliation_id = seal("B2_DEVELOPMENT_PILOT06_G03_RECONCILIATION_V1", reconciliation_core)
    reconciliation_artifact = {**reconciliation_core, "reconciliation_identity": reconciliation_id}
    receipt_core = {
        "schema_name": "batch2-development-pilot06-g03-receipt-v1", "schema_version": "1.0.0",
        "candidate_identity": open_pass["candidate_identity"], "candidate_raw_sha256": open_pass["candidate_raw_sha256"],
        "g03_validity": "VALID_BLIND_REVIEW", "open_recovery": {"primary": open_pass["primary_mechanism_description"],
                                                                    "role": open_pass["primary_role"], "confidence": open_pass["confidence"],
                                                                    "supporting": open_pass["supporting_mechanisms"]},
        "contrast_recovery": {"primary": contrast["primary_choice"], "role": contrast["primary_role"],
                                "confidence": contrast["confidence"], "supporting": contrast["supporting_choices"]},
        "shortcut_findings": {"open": open_pass["shortcut_assessment"], "contrast": contrast["shortcut_assessment"]},
        "reconciliation_identity": reconciliation_id, "reconciliation_classification": reconciliation,
        "g03b_performed": False, "g03c_performed": False, "candidate_modified": False,
        "eligibility": "NOT_ELIGIBLE_FOR_G03B_OR_POSITIVE_POOL_WITHOUT_SEPARATE_AMBIGUOUS_DISPOSITION_DECISION",
        "authority_matrix": {key: False for key in ("g03b", "g03c", "g04a", "g04b_pool_certification", "voice_review", "owner_review", "repair", "rewrite", "regeneration", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**receipt_core, "g03_receipt_identity": seal("B2_DEVELOPMENT_PILOT06_G03_RECEIPT_V1", receipt_core)}
    write("humor-mechanics-batch2-development-pilot06-g03-reconciliation-v1.json", reconciliation_artifact)
    write("humor-mechanics-batch2-development-pilot06-g03-receipt-v1.json", receipt)
    print(json.dumps({"g03_validity": receipt["g03_validity"], "reconciliation": reconciliation,
                      "reconciliation_identity": reconciliation_id, "g03_receipt_identity": receipt["g03_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
