"""Independent read-only audit of the local Bridge pre-ablation boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_editor_core_editorial_bridge_boundary as builder
from preflight_editor_core_editorial_bridge import ART, BOUNDARY_PATH, TOKEN_PATH, publication, sha, canonical
from project_editor_core_editorial_bridge_arms import projection


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def audit(path: Path = BOUNDARY_PATH, *, check_publication: bool = True) -> dict:
    value = json.loads(path.read_bytes())
    identity = value.pop("boundary_identity", None)
    require(identity == sha(canonical(value)), "boundary identity")
    require(value["status"] == "LOCAL_PREFLIGHT_ONLY_NO_ABLATION_AUTHORITY" and
            value["training_authorized"] is False and value["training_performed"] is False and
            value["optimizer_steps"] == 0 and value["development_parent_changed"] is False and
            value["adjudication_performed"] is False and value["promotion"] is False,
            "boundary execution state")
    require((value["published_dataset_commit"], value["published_dataset_tree"]) ==
            (builder.PUBLISHED_COMMIT, builder.PUBLISHED_TREE), "published Bridge base")
    require((value["parent_adapter_identity"], value["parent_checkpoint_identity"],
             value["base_model_identity"], value["rootfs_sha256"], value["driver_snapshot_manifest_identity"]) ==
            (builder.PARENT, builder.CHECKPOINT, builder.MODEL, builder.ROOTFS, builder.SNAPSHOT),
            "R2 model/runtime binding")
    require(value["naturalistic_evaluation"] == builder.protocol() and value["stop_rules"] == builder.stops(),
            "naturalistic/stop-rule contract")
    require(set(value["source_hashes"]) == set(builder.SOURCE_FILES), "source file closure")
    for name, expected in value["source_hashes"].items():
        require(sha((builder.ROOT / name).read_bytes()) == expected, f"source drift: {name}")
    token_raw = TOKEN_PATH.read_bytes()
    token = json.loads(token_raw)
    receipt_identity = token.pop("receipt_identity", None)
    require(receipt_identity == sha(canonical(token)) == value["token_audit_receipt_identity"] and
            sha(token_raw) == value["token_audit_blob_sha256"], "token receipt identity/blob")
    require(token["eos_checks"] == 336 and token["maximum_sequence_tokens"] <= 3072 and
            token["eos_token_id"] == 2 and token["model_loaded"] is False and
            token["optimizer_steps"] == 0 and token["training_performed"] is False,
            "tokenizer closure")
    arms = projection()
    require(arms["projection_identity"] == value["arm_projection_identity"] and
            {name: item["sha256"] for name, item in arms["arms"].items()} == value["arm_corpus_sha256"],
            "arm projection identity")
    published = publication(value) if check_publication else None
    return {"verdict": "PASS_LOCAL_BOUNDARY_ABLATIONS_BLOCKED", "blockers": 0,
            "boundary_identity": identity, "published": published,
            "token_receipt_identity": receipt_identity, "maximum_sequence_tokens": token["maximum_sequence_tokens"],
            "arm_projection_identity": arms["projection_identity"], "arm_count": len(arms["arms"]),
            "naturalistic_corpus_frozen": False, "ablation_training_authorized": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary", type=Path, default=BOUNDARY_PATH)
    args = parser.parse_args()
    print(json.dumps(audit(args.boundary), sort_keys=True))
