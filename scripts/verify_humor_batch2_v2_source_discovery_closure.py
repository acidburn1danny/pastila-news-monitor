"""Fail-closed verifier for the Batch 2 V2 discovery closure."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/humor-mechanics-curriculum-v1-batch2-v2-partitioned-source-discovery-closure-v2.json"
SCRIPT = ROOT / "scripts/audit_humor_batch2_v2_source_discovery_closure.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    require(data["plan_identity"] == "57419ff52730ccd20acf3c716c9502667d9f25e517570e18eeae7ec3d472da8a",
            "plan identity mismatch")
    require(data["authority"] == {
        "construction": False, "model_exposure": False, "production_routing": False,
        "runtime_integration": False, "source_discovery": True,
        "surface_generation": False, "training": False,
    }, "authority widened")
    require(data["eligibility"]["later_construction_decision"] == [], "construction eligibility not empty")
    require(data["execution"]["blind_content_queries"] == 0 and data["execution"]["blind_atom_reads"] == 0,
            "blind content access observed")
    require(all(data["pipeline_invariants"].values()), "pipeline invariant false")
    contaminated = {f.get("event_id"): f for f in data["families"] if f["partition"] == "BLIND_CONTAMINATED"}
    require(set(contaminated) == {1538, 2617}, "permanent blind-contamination set mismatch")
    for event_id, family in contaminated.items():
        require(family["status"] == "PERMANENTLY_BLIND_CONTAMINATED_NO_REASSIGNMENT_NO_DOWNSTREAM_USE",
                f"{event_id}: contamination not permanent")
        require("span_checks" not in family and "metadata_articles" not in family,
                f"{event_id}: blind content leaked")
        require(family["permitted_use_closure"] == "NOT_REOPENED_BLIND_CONTAMINATION_IS_DISPOSITIVE" and
                family["immutable_capture_closure"] == "NOT_REOPENED_BLIND_CONTAMINATION_IS_DISPOSITIVE",
                f"{event_id}: contaminated family was improperly reopened")
        require(not family["construction_eligible"], f"{event_id}: downstream use enabled")
    require(len(data["replacement_blind_evaluation_families"]) >= 2, "insufficient blind replacements")
    for family in data["replacement_blind_evaluation_families"]:
        require(family["content_queries"] == family["atom_reads"] == 0, "replacement blind exposure")
        require("event_id" not in family and "metadata_articles" not in family, "replacement blind identity leaked")
        require(not family["construction_eligible"], "blind replacement construction enabled")
    expected_categories = {"DEVELOPMENT", "CURRICULUM_CANDIDATE", "BLIND_EVALUATION",
                           "PROVISIONAL", "BLIND_CONTAMINATED", "REJECTED"}
    require(set(data["canonical_inventory"]) == expected_categories, "inventory category mismatch")
    nonblind = [f for f in data["families"] if f.get("event_id") not in {1538, 2617}]
    require({f["event_id"] for f in nonblind} == {2096, 2472, 2111, 2360, 2365, 734},
            "owner-final investigation set mismatch")
    for family in nonblind:
        require(not family["construction_eligible"], f"{family['event_id']}: silently promoted")
        require(family["immutable_capture_status"] == "HASH_BOUND_BUT_SOURCE_BYTES_NOT_ARCHIVED_IN_GIT",
                f"{family['event_id']}: immutable-capture overclaim")
        require(all(review["status"] not in {"PASS", "PERMITTED"} for review in family["permitted_use_reviews"]),
                f"{family['event_id']}: permitted-use overclaim")
        for check in family["span_checks"]:
            require("recorded_character_coordinates_valid" in check and
                    "recorded_utf8_byte_coordinates_valid" in check and
                    "canonical_character_coordinates" in check and
                    "canonical_utf8_byte_coordinates" in check,
                    f"{family['event_id']}: coordinate dimensions collapsed")
    ledger_classes = [item["classification"] for item in data["contamination_exposure_ledger"]]
    require(ledger_classes.count("BLIND_CONTAMINATED_PERMANENT") == 2, "contamination ledger incomplete")
    require(ledger_classes.count("PRISTINE_BLIND_EVALUATION_RESERVED_METADATA_ONLY") >= 2,
            "blind reservation exposure ledger incomplete")
    source = SCRIPT.read_text(encoding="utf-8")
    branch = source.index("if event_id in PERMANENTLY_BLIND_CONTAMINATED:")
    atom_read = source.index("atoms = load_atoms(directory)", branch)
    branch_continue = source.index("continue", branch)
    require(branch < branch_continue < atom_read, "blind branch no longer blocks atom access")
    print(json.dumps({
        "verdict": "PASS_ZERO_CONSTRUCTION_SOURCE_DISCOVERY_CLOSURE",
        "artifact_sha256": hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(),
        "families_checked": len(data["families"]),
        "blind_replacements_checked": len(data["replacement_blind_evaluation_families"]),
        "construction_authority": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
