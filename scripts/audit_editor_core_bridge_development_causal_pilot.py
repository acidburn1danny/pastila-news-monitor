"""Fixture-only successor audit. This module cannot start training or inference."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from audit_editor_core_bridge_a1_a2_fixture_gate import audit as audit_arm_isolation
from audit_editor_core_editorial_mechanics_bridge import audit as audit_corpus
from build_editor_core_editorial_mechanics_bridge import ART, PREFIX, canonical, compact, sha

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/artifacts/editor-core-editorial-bridge-development-causal-pilot-v1.json"
PROTOCOL_SHA256 = "6eed58beaadf277d30e60282260bc9ef513d90fa5b49a3bac03f64ad56a2e0bb"
OPERATORS = (
    "FACT_SELECTION", "QUALIFIED_COMPRESSION", "CHRONOLOGICAL_ORDER",
    "PRECISE_ATTRIBUTION", "SUPPORTED_CONTRAST", "FACTUAL_TRANSITION",
    "NATURAL_ROMANIAN", "EPISTEMIC_GUARD",
)


def load_jsonl(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("development request truncation")
    rows = [json.loads(line) for line in raw.splitlines()]
    if any(compact(row).encode("utf-8") != line for row, line in zip(rows, raw.splitlines(), strict=True)):
        raise ValueError("development request noncanonical")
    return rows


def decide_fixture(case_signs: dict[str, tuple[str, str]], seed_nets: tuple[int, int, int],
                   *, safety_harm: bool = False, severe_romanian_regression: bool = False,
                   unresolved_safety_dispute: bool = False) -> str:
    """Apply predeclared rule to synthetic fixture signs, never to model outputs."""
    if len(case_signs) != 24 or len(seed_nets) != 3:
        raise ValueError("fixture cardinality")
    if safety_harm:
        return "STOP"
    if severe_romanian_regression or unresolved_safety_dispute:
        return "REVISE"
    if any(op not in OPERATORS or sign not in ("WIN", "LOSS", "TIE", "INDETERMINATE")
           for op, sign in case_signs.values()):
        raise ValueError("fixture score schema")
    if (set(case_signs) != {f"case-{index}" for index in range(24)}
            or Counter(op for op, _ in case_signs.values()) != {op: 3 for op in OPERATORS}):
        raise ValueError("fixture case/operator balance")
    wins = [op for op, sign in case_signs.values() if sign == "WIN"]
    losses = sum(sign == "LOSS" for _, sign in case_signs.values())
    if (len(wins) >= 6 and losses <= 2 and len(set(wins)) >= 4
            and sum(net > 0 for net in seed_nets) >= 2):
        return "CONTINUE_TO_NATURALISTIC_INVESTMENT_ONLY"
    if not wins and all(net <= 0 for net in seed_nets):
        return "STOP_TARGET_DESIGN_UNDER_THIS_RECIPE"
    return "REVISE"


def aggregate_fixture_seed_signs(seed_signs: dict[str, tuple[str, tuple[str, str, str]]]
                                 ) -> tuple[dict[str, tuple[str, str]], tuple[int, int, int]]:
    """Keep three matched seeds inside each case; never count seeds as cases."""
    if (len(seed_signs) != 24 or set(seed_signs) != {f"case-{index}" for index in range(24)}
            or Counter(op for op, _ in seed_signs.values()) != {op: 3 for op in OPERATORS}):
        raise ValueError("fixture seed case/operator balance")
    nets = [0, 0, 0]
    cases = {}
    for case_id, (operator, signs) in seed_signs.items():
        if len(signs) != 3 or any(sign not in ("WIN", "LOSS", "TIE", "INDETERMINATE") for sign in signs):
            raise ValueError("fixture seed sign schema")
        for index, sign in enumerate(signs):
            nets[index] += (sign == "WIN") - (sign == "LOSS")
        case_sign = "WIN" if signs.count("WIN") >= 2 else "LOSS" if signs.count("LOSS") >= 2 else "TIE"
        cases[case_id] = (operator, case_sign)
    return cases, tuple(nets)


def audit(artifacts: Path = ART, protocol_path: Path = PROTOCOL) -> dict:
    raw = protocol_path.read_bytes()
    if sha(raw) != PROTOCOL_SHA256:
        raise ValueError("successor protocol byte identity")
    protocol = json.loads(raw)
    if (protocol["status"] != "LOCAL_DESIGN_FIXTURE_ONLY_NO_REAL_RUN_AUTHORITY"
            or protocol["candidate_arms"] != ["A1", "A2"]
            or protocol["evaluation_splits_allowed"] != ["SYNTHETIC_DEVELOPMENT_ONLY"]
            or protocol["development_requests"] != 24
            or protocol["seeds"] != [271828, 314159, 161803]
            or protocol["real_runs_authorized"] is not False
            or protocol["optimizer_steps_authorized"] != 0
            or protocol["parent_change_authorized"] is not False
            or protocol["promotion_authorized"] is not False):
        raise ValueError("successor scope or authority")
    corpus = audit_corpus(artifacts)
    if (corpus["plan_identity"] != protocol["published_plan_identity"]
            or corpus["manifest_identity"] != "a4649f59a5a536c688e7d3741bc46e82d8997dc6a8c04948a25424528102ba3a"):
        raise ValueError("published corpus identity")
    isolation = audit_arm_isolation(artifacts)
    if (isolation["published_plan_identity"] != protocol["published_plan_identity"]
            or isolation["parent_adapter_identity"] != protocol["parent_adapter_identity"]):
        raise ValueError("arm or parent binding")
    requests = load_jsonl(artifacts / f"{PREFIX}-development-requests.jsonl")
    holdout = load_jsonl(artifacts / f"{PREFIX}-holdout-requests.jsonl")
    if (len(requests) != 24 or len(holdout) != 24
            or Counter(row["operator"] for row in requests) != {op: 3 for op in OPERATORS}
            or {row["example_id"] for row in requests} & {row["example_id"] for row in holdout}
            or any(row["split"] != "DEVELOPMENT" or len(row["messages"]) != 2 for row in requests)):
        raise ValueError("development/holdout isolation")
    core = {
        "schema": "editor-core-bridge-development-causal-pilot-fixture-gate",
        "schema_version": 1,
        "verdict": "PASS_FIXTURE_ONLY_REAL_RUN_BLOCKED",
        "successor_protocol_sha256": sha(raw),
        "published_plan_identity": corpus["plan_identity"],
        "published_manifest_identity": corpus["manifest_identity"],
        "parent_adapter_identity": protocol["parent_adapter_identity"],
        "development_requests_sha256": sha((artifacts / f"{PREFIX}-development-requests.jsonl").read_bytes()),
        "development_cases": len(requests),
        "holdout_cases_excluded": len(holdout),
        "matched_runs_planned": 6,
        "raw_response_slots_maximum": 24 * 6,
        "new_target_only_differences": isolation["new_target_only_differences"],
        "identical_replay_rows": isolation["identical_replay_rows"],
        "model_loaded": False,
        "inference": False,
        "optimizer_steps": 0,
        "training_performed": False,
        "real_run_ready": False,
    }
    return {**core, "fixture_gate_identity": sha(canonical(core))}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
