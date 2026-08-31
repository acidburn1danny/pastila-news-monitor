"""Reveal Pilot 04 mapping after blind freeze and reconcile G03."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BLIND_COMMIT = "e465603fcce0c89b6545ae0cc0f100df37b6a22b"
ASSIGNMENT_COMMIT = "02ab072957e748cc5df0102487668e6ec1cc7b1d"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-g03-"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-sealed-assignment-mapping-v1.json"


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
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BLIND_COMMIT, "HEAD")
    open_pass, contrast = load(BLIND_COMMIT, PREFIX + "pass-a-v1.json"), load(BLIND_COMMIT, PREFIX + "pass-b-v1.json")
    isolation, choice = load(BLIND_COMMIT, PREFIX + "blind-isolation-v1.json"), load(BLIND_COMMIT, PREFIX + "choice-set-v1.json")
    for value, field, namespace in (
        (choice, "choice_set_identity", "B2_DEVELOPMENT_PILOT04_G03_CHOICE_SET_V1"),
        (open_pass, "pass_identity", "B2_DEVELOPMENT_PILOT04_G03_OPEN_PASS_V1"),
        (contrast, "pass_identity", "B2_DEVELOPMENT_PILOT04_G03_CONTRAST_PASS_V1"),
        (isolation, "isolation_identity", "B2_DEVELOPMENT_PILOT04_G03_BLIND_ISOLATION_V1"),
    ):
        core = dict(value); identity = core.pop(field)
        require(seal(namespace, core) == identity, field)
    require(isolation["status"] == "BLIND_PASSES_FROZEN_AWAITING_RECONCILIATION", "status")
    require(isolation["sealed_mapping_access"] is False and isolation["mapping_revealed"] is False, "premature mapping")
    mapping = load(ASSIGNMENT_COMMIT, MAPPING_PATH)
    mapping_core = dict(mapping); mapping_id = mapping_core.pop("sealed_assignment_identity")
    require(seal("B2_DEVELOPMENT_PILOT04_SEALED_ASSIGNMENT_V1", mapping_core) == mapping_id, "mapping seal")
    target = mapping["target_mapping"]
    require(target["mechanism_name"] == "Absurd Logical Extension", "target")
    opened, closed = open_pass["result"], contrast["result"]
    open_alignment = (opened["primary_role"] == "DOMINANT" and opened["confidence"] == "HIGH"
                      and "lanț inferențial absurd" in opened["primary_mechanism"]
                      and "acreditare nevalidă–excludere–demonstrarea absurdă" in opened["alternative_comparison"])
    closed_recovery = (closed["primary_choice"] == target["mechanism_name"] and closed["primary_role"] == "DOMINANT"
                       and closed["confidence"] == "HIGH"
                       and set(closed["comparisons"]) == set(choice["displayed_order"]) - {target["mechanism_name"]})
    require(open_alignment and closed_recovery, "recovery mismatch")
    classification = "TARGET_RECOVERED_DOMINANT"
    reconciliation_core = {
        "schema_name": "batch2-development-pilot04-g03-reconciliation-v1", "schema_version": "1.0.0",
        "candidate_identity": "cf34033fb7017ff29146524108d4cb3fcbf8229681d054d2085dbaba294436e1",
        "blind_pass_commit": BLIND_COMMIT, "assignment_commit": ASSIGNMENT_COMMIT,
        "sealed_assignment_identity": mapping_id, "mapping_revealed_after_blind_freeze": True,
        "sealed_target": target,
        "open_pass": {"pass_identity": open_pass["pass_identity"], "verbatim_primary": opened["primary_mechanism"],
                      "verbatim_primary_role": opened["primary_role"], "verbatim_supporting": opened["supporting_mechanisms"],
                      "structural_alignment_with_sealed_target": "PASS_DEPENDENT_PREMISE_TO_ABSURD_CONSEQUENCE_CHAIN",
                      "posthoc_label_rewrite": False},
        "contrast_pass": {"pass_identity": contrast["pass_identity"], "primary_choice": closed["primary_choice"],
                          "primary_role": closed["primary_role"], "supporting_choices": closed["supporting_choices"],
                          "confidence": closed["confidence"], "all_close_alternatives_contrasted": True},
        "substantive_disagreement": False,
        "reconciliation_rationale": "OPEN_PASS_RECOVERS_THE_DEPENDENT_ABSURD_INFERENCE_CHAIN_WITHOUT_TAXONOMY_TERMS;_CLOSED_PASS_RECOVERS_THE_EXACT_TARGET_DOMINANT_AND_IDENTIFIES_RECLASSIFICATION_AS_SUPPORTING",
        "classification": classification,
    }
    reconciliation = {**reconciliation_core, "reconciliation_identity": seal("B2_DEVELOPMENT_PILOT04_G03_RECONCILIATION_V1", reconciliation_core)}
    receipt_core = {
        "schema_name": "batch2-development-pilot04-g03-receipt-v1", "schema_version": "1.0.0",
        "candidate_identity": reconciliation_core["candidate_identity"],
        "candidate_raw_sha256": "e231a549685103da5c6e0e4f9b9e93459d86e7c7ae0247ad11f15d55a3426b0b",
        "creative_premise_family_id": "726eb45203c35592ea2781ac778b7147fd97794d907f0973861acbfa1e3bc6fc",
        "g02_receipt_identity": "d1e339796733a75423b4255bc90fc440c5c572ada4628954258f92ecde963cd3",
        "g02c_conformance_receipt_identity": "35b73a375473c0d49ea671785e4db4d1b23d7568ea8c06d38fc5d0014ffd41f8",
        "choice_set_identity": choice["choice_set_identity"], "open_pass_identity": open_pass["pass_identity"],
        "contrast_pass_identity": contrast["pass_identity"], "blind_isolation_identity": isolation["isolation_identity"],
        "reconciliation_identity": reconciliation["reconciliation_identity"],
        "g03_validity_status": "VALID_BLIND_REVIEW", "reconciliation_classification": classification,
        "target_dominant_recovery_established": True, "candidate_modified": False,
        "g03b_performed": False, "g03c_performed": False, "romanian_naturalness_review_performed": False,
        "voice_review_performed": False, "owner_review_performed": False,
        "authority_matrix": {key: False for key in ("g03b", "g03c", "romanian_naturalness_review", "voice_review",
                                                     "owner_review", "repair", "rewrite", "regeneration", "training",
                                                     "runtime_integration", "production_routing", "g04b_pool_certification")},
    }
    receipt = {**receipt_core, "g03_receipt_identity": seal("B2_DEVELOPMENT_PILOT04_G03_RECEIPT_V1", receipt_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot04-candidate01-g03-reconciliation-v1.json", reconciliation),
                        ("humor-mechanics-batch2-development-pilot04-candidate01-g03-receipt-v1.json", receipt)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g03_validity_status": receipt["g03_validity_status"], "open_primary": opened["primary_mechanism"],
                      "contrast_primary": closed["primary_choice"], "contrast_supporting": closed["supporting_choices"],
                      "reconciliation_classification": classification,
                      "reconciliation_identity": reconciliation["reconciliation_identity"],
                      "g03_receipt_identity": receipt["g03_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
