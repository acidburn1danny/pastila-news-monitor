"""Audit the planning-only VNext VOICE model candidate plan."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.build_editor_vnext_voice_model_candidate_plan_v1 import RESULT, build
except ModuleNotFoundError:
    from build_editor_vnext_voice_model_candidate_plan_v1 import RESULT, build


ROOT = Path(__file__).resolve().parents[1]


def audit() -> dict:
    value = json.loads(RESULT.read_text(encoding="utf-8"))
    if value != build():
        raise ValueError("plan is not reproducible")
    snapshots = json.loads((ROOT / "docs/artifacts/editor-core-text-realizer-model-acquisition-v1-snapshots.json").read_text(encoding="utf-8"))
    planned = {item["revision"]: item for item in value["candidates"] if "snapshot_identity" in item}
    for source in snapshots["models"]:
        candidate = planned[source["revision"]]
        if (candidate["snapshot_identity"], candidate["snapshot_bytes"], candidate["license"]) != (source["snapshot_identity"], source["total_bytes"], source["license"]):
            raise ValueError("candidate snapshot drift")
    if value["acquisition"]["authorized"] or value["bakeoff"]["authorized"]:
        raise ValueError("plan granted execution authority")
    if any(value[key] for key in ("model_downloaded", "model_loaded", "inference_performed", "training_performed")):
        raise ValueError("planning boundary violated")
    if value["product_root_modified"] or value["product_lock_modified"] or value["legacy_dependency_count"]:
        raise ValueError("VNext invariant drift")
    return {"status": "PASS", "plan_identity": value["plan_identity"], "candidates": 3}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
