"""Reveal the Pilot 02 mapping only after blind-pass freeze and reconcile G03."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BLIND_COMMIT = "0af2097ccdf0aa03dc0a9f6dcb3f58a67d7649f5"
ASSIGNMENT_COMMIT = "2edbc5d8f9916508f31ded7a1453be3c021769da"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03-"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-sealed-assignment-mapping-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BLIND_COMMIT,
            "HEAD differs from blind-pass freeze")
    open_pass = load(BLIND_COMMIT, PREFIX + "pass-a-v1.json")
    contrast = load(BLIND_COMMIT, PREFIX + "pass-b-v1.json")
    isolation = load(BLIND_COMMIT, PREFIX + "blind-isolation-v1.json")
    choice = load(BLIND_COMMIT, PREFIX + "choice-set-v1.json")
    for value, field, namespace in (
        (choice, "choice_set_identity", "B2_DEVELOPMENT_PILOT02_G03_CHOICE_SET_V1"),
        (open_pass, "pass_identity", "B2_DEVELOPMENT_PILOT02_G03_OPEN_PASS_V1"),
        (contrast, "pass_identity", "B2_DEVELOPMENT_PILOT02_G03_CONTRAST_PASS_V1"),
        (isolation, "isolation_identity", "B2_DEVELOPMENT_PILOT02_G03_BLIND_ISOLATION_V1"),
    ):
        core = dict(value); identity = core.pop(field)
        require(seal(namespace, core) == identity, f"blind seal {field}")
    require(isolation["status"] == "BLIND_PASSES_FROZEN_AWAITING_RECONCILIATION", "isolation status")
    require(isolation["sealed_mapping_access"] is False and isolation["mapping_revealed"] is False, "premature mapping")

    # This is the first mapping read in the G03 workflow and occurs only after the
    # immutable blind-pass commit above has been verified.
    mapping = load(ASSIGNMENT_COMMIT, MAPPING_PATH)
    mapping_core = dict(mapping); mapping_identity = mapping_core.pop("sealed_assignment_identity")
    require(seal("B2_DEVELOPMENT_PILOT02_SEALED_ASSIGNMENT_V1", mapping_core) == mapping_identity, "mapping seal")
    target = mapping["target_mapping"]
    require(target["mechanism_name"] == "Absurd Logical Extension", "sealed target")

    open_result, contrast_result = open_pass["result"], contrast["result"]
    open_structural_alignment = (
        open_result["primary_role"] == "DOMINANT"
        and open_result["confidence"] == "HIGH"
        and open_result["primary_mechanism"] == "paradox temporal autoanulant"
        and "cauză" in open_result["defining_surface_operation"]
        and "anulează" in open_result["defining_surface_operation"]
        and "escaladare logică absurdă" in open_result["supporting_mechanisms"]
        and open_result["strongest_alternative"] not in choice["displayed_order"]
    )
    closed_target_recovery = (
        contrast_result["primary_choice"] == target["mechanism_name"]
        and contrast_result["primary_role"] == "DOMINANT"
        and contrast_result["confidence"] == "HIGH"
        and set(contrast_result["comparisons"]) == set(choice["displayed_order"]) - {target["mechanism_name"]}
    )
    require(open_structural_alignment and closed_target_recovery, "blind recovery mismatch")
    reconciliation_classification = "TARGET_RECOVERED_DOMINANT"
    reconciliation_core = {
        "schema_name": "batch2-development-pilot02-g03-reconciliation-v1",
        "schema_version": "1.0.0",
        "candidate_identity": "4cc6bceef84e29d07e19d60dbbb1992b33fcb8af67373647f5fb8fedfce1d98c",
        "blind_pass_commit": BLIND_COMMIT,
        "assignment_commit": ASSIGNMENT_COMMIT,
        "sealed_assignment_identity": mapping_identity,
        "mapping_revealed_after_blind_freeze": True,
        "sealed_target": target,
        "open_pass": {
            "pass_identity": open_pass["pass_identity"],
            "verbatim_primary": open_result["primary_mechanism"],
            "verbatim_primary_role": open_result["primary_role"],
            "verbatim_supporting": open_result["supporting_mechanisms"],
            "structural_alignment_with_sealed_target": "PASS_PREMISE_CAUSE_CHAIN_TO_ABSURD_SELF_CANCELLATION",
            "posthoc_label_rewrite": False,
        },
        "contrast_pass": {
            "pass_identity": contrast["pass_identity"],
            "primary_choice": contrast_result["primary_choice"],
            "primary_role": contrast_result["primary_role"],
            "confidence": contrast_result["confidence"],
            "all_close_alternatives_contrasted": True,
        },
        "substantive_disagreement": False,
        "reconciliation_rationale": "OPEN_PASS_USES_A_MORE_SPECIFIC_NON_TAXONOMY_DESCRIPTION_OF_THE_SAME_PREMISE_TO_DEPENDENT_ABSURD_CONSEQUENCE_CHAIN;_CLOSED_PASS_RECOVERS_THE_EXACT_TARGET_DOMINANT",
        "classification": reconciliation_classification,
    }
    reconciliation = {**reconciliation_core, "reconciliation_identity": seal("B2_DEVELOPMENT_PILOT02_G03_RECONCILIATION_V1", reconciliation_core)}
    receipt_core = {
        "schema_name": "batch2-development-pilot02-g03-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": reconciliation_core["candidate_identity"],
        "candidate_raw_sha256": "5c50ca8e4ae5ea32301c02ec8ea4104482bbc9c8e3c7e8314516d09aeb591fd3",
        "creative_premise_family_id": "ccb8ffaa1f8bd4f1cc40042854a76e73c3fb99d08f359da2e7ea952796bd7467",
        "g02_receipt_identity": "adf92833cf079d5df823c9d899618da8f8f8367cab3215f96be5ad6fd0d3c7f2",
        "g02c_conformance_receipt_identity": "572f6cecf8968fa3f7fef26ad311fefc8ad4caddc8ba89060a10096279645577",
        "choice_set_identity": choice["choice_set_identity"],
        "open_pass_identity": open_pass["pass_identity"],
        "contrast_pass_identity": contrast["pass_identity"],
        "blind_isolation_identity": isolation["isolation_identity"],
        "reconciliation_identity": reconciliation["reconciliation_identity"],
        "g03_validity_status": "VALID_BLIND_REVIEW",
        "reconciliation_classification": reconciliation_classification,
        "target_dominant_recovery_established": True,
        "candidate_modified": False,
        "g03b_performed": False,
        "g03c_performed": False,
        "romanian_naturalness_review_performed": False,
        "voice_review_performed": False,
        "owner_review_performed": False,
        "authority_matrix": {key: False for key in (
            "g03b", "g03c", "romanian_naturalness_review", "voice_review", "owner_review", "repair",
            "rewrite", "regeneration", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**receipt_core, "g03_receipt_identity": seal("B2_DEVELOPMENT_PILOT02_G03_RECEIPT_V1", receipt_core)}
    for name, value in (
        ("humor-mechanics-batch2-development-pilot02-candidate01-g03-reconciliation-v1.json", reconciliation),
        ("humor-mechanics-batch2-development-pilot02-candidate01-g03-receipt-v1.json", receipt),
    ):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8", newline="\n")
    print(json.dumps({"g03_validity_status": receipt["g03_validity_status"],
                      "open_primary": open_result["primary_mechanism"],
                      "contrast_primary": contrast_result["primary_choice"],
                      "reconciliation_classification": reconciliation_classification,
                      "reconciliation_identity": reconciliation["reconciliation_identity"],
                      "g03_receipt_identity": receipt["g03_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
