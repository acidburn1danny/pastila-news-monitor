from __future__ import annotations

import hashlib
import json
from pathlib import Path

from editor_core_factual_setup_r2_anchored_contrastive_safety_fixture_v1 import ARMS, FAILURE_CLASSES, LAYER_GROUPS, SEEDS, validate_pair


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
P = "editor-core-factual-setup-r2-anchored-contrastive-safety-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: dict, field: str) -> str:
    core = dict(value); claimed = core.pop(field)
    actual = hashlib.sha256(canonical(core)).hexdigest()
    if claimed != actual:
        raise ValueError(f"{field} mismatch")
    return actual


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol = json.loads((ART / f"{P}-protocol.json").read_text(encoding="utf-8"))
    manifest = json.loads((ART / f"{P}-manifest.json").read_text(encoding="utf-8"))
    probe = json.loads((ART / f"{P}-gradient-probe.json").read_text(encoding="utf-8"))
    boundary = json.loads((ART / f"{P}-execution-boundary.json").read_text(encoding="utf-8"))
    pairs_path = ART / f"{P}-minimal-pairs.jsonl"; retention_path = ART / f"{P}-retention-anchors.jsonl"
    pairs = [json.loads(line) for line in pairs_path.read_text(encoding="utf-8").splitlines()]
    retention = [json.loads(line) for line in retention_path.read_text(encoding="utf-8").splitlines()]
    identities = {
        "protocol": identity(protocol, "protocol_identity"),
        "pack": identity(manifest, "pack_identity"),
        "gradient_probe": identity(probe, "gradient_probe_identity"),
        "boundary": identity(boundary, "boundary_identity"),
    }
    if protocol["parent"] != "R2_STEP_9" or protocol["weighted_sft_t1s0_line"] != "CLOSED_REFERENCE_ONLY":
        raise ValueError("lineage")
    if tuple(protocol["seeds"]) != SEEDS or tuple(boundary["arms"]) != ARMS or tuple(boundary["seeds"]) != SEEDS:
        raise ValueError("factorial binding")
    if len(boundary["slots"]) != 12 or len({row["slot_id"] for row in boundary["slots"]}) != 12:
        raise ValueError("slot inventory")
    if any(row["real_execution_authorized"] or row["output_root_policy"] != "DISTINCT_EMPTY" for row in boundary["slots"]):
        raise ValueError("slot authority")
    if len(pairs) != 48 or len(retention) != 24:
        raise ValueError("pack rows")
    coverage = {name: 0 for name in FAILURE_CLASSES}
    for pair in pairs:
        validate_pair(pair); coverage[pair["failure_class"]] += 1
    if set(coverage.values()) != {8} or any(row["historical_holdout"] for row in retention):
        raise ValueError("coverage/isolation")
    if tuple(probe["failure_classes"]) != FAILURE_CLASSES or tuple(probe["layer_groups"]) != LAYER_GROUPS:
        raise ValueError("gradient probe matrix")
    if manifest["minimal_pairs_sha256"] != file_sha(pairs_path) or manifest["retention_anchors_sha256"] != file_sha(retention_path):
        raise ValueError("pack byte identity")
    forbidden = ("model_load_authorized", "optimizer_creation_authorized", "training_authorized", "inference_authorized", "parent_selection_authority")
    if any(protocol[field] for field in forbidden) or any(boundary[field] for field in forbidden):
        raise ValueError("forbidden authority")
    if protocol["historical_holdouts_allowed"] or boundary["historical_holdouts_allowed"]:
        raise ValueError("holdout authority")
    print(json.dumps({"status": "PASS", "blockers": 0, "identities": identities, "pairs": 48, "retention": 24, "arms": 4, "seeds": 3, "slots": 12, "gradient_cells": 36, "model_loaded": False, "optimizer_created": False, "training_performed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
