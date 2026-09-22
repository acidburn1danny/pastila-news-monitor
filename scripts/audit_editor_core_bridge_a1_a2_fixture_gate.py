"""Fail-closed fixture-only A1/A2 causal-route audit; no model or optimizer."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from build_editor_core_editorial_mechanics_bridge import ART, canonical, sha
from project_editor_core_editorial_bridge_arms import arm_rows


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/artifacts/editor-core-editorial-bridge-staged-a1-a2-v1.json"
EXPECTED_PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
EXPECTED_PLAN = "4caa3811ff1eb9e19bc0e460edd760755e224100953595e5a5c4b91ab73cb6ef"
EXPECTED_PROTOCOL_SHA256 = "c61a04d9a41f8c165a16a0a3296057a28310266c8088c621bff18693fcb13060"
SEEDS = [271828, 314159, 161803]


def check_pairs(control: list[dict], mechanics: list[dict]) -> dict:
    """Prove only the 48 new assistant targets differ; replay is byte-identical."""
    if len(control) != len(mechanics) or len(control) != 96:
        raise ValueError("arm row count")
    seen_control: set[str] = set()
    seen_mechanics: set[str] = set()
    changed = 0
    for index, (left, right) in enumerate(zip(control, mechanics, strict=True)):
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError("arm row type")
        if left.get("example_id") in seen_control or right.get("example_id") in seen_mechanics:
            raise ValueError("arm duplicate id")
        seen_control.add(left.get("example_id"))
        seen_mechanics.add(right.get("example_id"))
        if index >= 48:
            if canonical(left) != canonical(right):
                raise ValueError("replay drift")
            continue
        if {key: value for key, value in left.items() if key != "messages"} != \
                {key: value for key, value in right.items() if key != "messages"}:
            raise ValueError("new row identity or source drift")
        messages_left, messages_right = left.get("messages"), right.get("messages")
        if not isinstance(messages_left, list) or not isinstance(messages_right, list) or \
                len(messages_left) != len(messages_right) or len(messages_left) != 3 or \
                [item.get("role") for item in messages_left] != ["system", "user", "assistant"] or \
                [item.get("role") for item in messages_right] != ["system", "user", "assistant"]:
            raise ValueError("new row message shape")
        if canonical(messages_left[:2]) != canonical(messages_right[:2]):
            raise ValueError("instruction or source drift")
        if messages_left[2]["content"] == messages_right[2]["content"]:
            raise ValueError("target contrast absent")
        if set(messages_left[2]) != {"role", "content"} or set(messages_right[2]) != {"role", "content"}:
            raise ValueError("assistant message scope")
        changed += 1
    if len(seen_control) != 96 or len(seen_mechanics) != 96 or changed != 48:
        raise ValueError("arm closure")
    return {"new_target_only_differences": changed, "identical_replay_rows": 48}


def audit(artifacts: Path = ART, protocol_path: Path = PROTOCOL) -> dict:
    protocol_bytes = protocol_path.read_bytes()
    if sha(protocol_bytes) != EXPECTED_PROTOCOL_SHA256:
        raise ValueError("staged protocol byte identity")
    protocol = json.loads(protocol_bytes)
    if protocol.get("status") != "DESIGN_ONLY_NO_EXECUTION_AUTHORITY" or \
            protocol.get("published_bridge_plan_identity") != EXPECTED_PLAN or \
            protocol.get("parent_adapter_identity") != EXPECTED_PARENT or \
            protocol.get("contrast", {}).get("arms") != ["A1", "A2"] or \
            protocol["contrast"].get("changed_factor_only") != \
            "TARGET_DESIGN_LITERAL_SAFE_CONTROL_VS_NEUTRAL_EDITORIAL_MECHANICS" or \
            protocol["contrast"].get("seeds") != SEEDS or \
            protocol["contrast"].get("real_runs_authorized") is not False or \
            protocol.get("training_authorized") is not False or \
            protocol.get("optimizer_steps_authorized") != 0 or \
            protocol.get("parent_change_authorized") is not False:
        raise ValueError("staged protocol binding or authority")
    rows_a1, config_a1 = arm_rows(artifacts, "A1")
    rows_a2, config_a2 = arm_rows(artifacts, "A2")
    cfg_a1, cfg_a2 = copy.deepcopy(config_a1), copy.deepcopy(config_a2)
    if cfg_a1.pop("target") != "LITERAL_SAFE_CONTROL" or \
            cfg_a2.pop("target") != "NEUTRAL_EDITORIAL_MECHANICS":
        raise ValueError("target design binding")
    cfg_a1.pop("id")
    cfg_a2.pop("id")
    if cfg_a1 != cfg_a2:
        raise ValueError("non-target arm factor drift")
    pair_result = check_pairs(rows_a1, rows_a2)
    core = {"schema": "editor-core-bridge-a1-a2-fixture-gate", "schema_version": 1,
            "verdict": "PASS_FIXTURE_ONLY_REAL_TRAINING_BLOCKED", "blockers_for_fixture_gate": 0,
            "published_plan_identity": EXPECTED_PLAN, "parent_adapter_identity": EXPECTED_PARENT,
            "staged_protocol_sha256": sha(protocol_bytes),
            "a1_rows_sha256": sha(b"".join(canonical(row) + b"\n" for row in rows_a1)),
            "a2_rows_sha256": sha(b"".join(canonical(row) + b"\n" for row in rows_a2)),
            **pair_result, "seeds": SEEDS, "model_loaded": False,
            "inference": False, "optimizer_steps": 0, "training_performed": False,
            "naturalistic_16_admitted": False, "real_run_ready": False}
    return {**core, "fixture_gate_identity": sha(canonical(core))}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
