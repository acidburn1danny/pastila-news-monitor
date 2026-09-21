"""Independent, read-only closure audit for the editorial mechanics bridge."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from build_editor_core_editorial_mechanics_bridge import (
    ART, KEY_ORDER, OPERATORS, PARENT_ADAPTER, PARENT_CHECKPOINT, PREFIX,
    REPLAY_SOURCES, canonical, sha, source_contract,
)

LABELS = (
    "train-mechanics", "train-control", "train-mechanics-generic", "train-control-generic",
    "replay-baseline", "replay-protective",
    "development-requests", "development-answer-key", "holdout-requests",
    "holdout-answer-key", "counterexamples", "plan",
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def load_json(path: Path) -> dict:
    data = path.read_bytes()
    value = json.loads(data)
    require(json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n" == data, f"noncanonical JSON: {path.name}")
    return value


def load_rows(path: Path) -> list[dict]:
    raw = path.read_bytes()
    require(raw.endswith(b"\n"), f"truncated JSONL: {path.name}")
    rows = [json.loads(line) for line in raw.splitlines()]
    require(all(json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() == line
                for row, line in zip(rows, raw.splitlines())), f"noncanonical JSONL: {path.name}")
    return rows


def request(row: dict) -> dict:
    messages = row["messages"]
    require(len(messages) >= 2 and messages[0]["role"] == "system" and messages[1]["role"] == "user", "request message contract")
    return json.loads(messages[1]["content"].split("\nINPUT=", 1)[1])


def target(row: dict) -> dict:
    require(len(row["messages"]) == 3 and row["messages"][2]["role"] == "assistant", "train target contract")
    value = json.loads(row["messages"][2]["content"])
    require(tuple(value) == KEY_ORDER, "response key order")
    return value


def semantic(row: dict) -> str:
    payload = request(row)
    return " ".join([payload["request"], *(span["text"] for span in payload["authority_spans"])])


def shingles(value: str) -> set[tuple[str, ...]]:
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", value).casefold())
    return {tuple(words[i:i + 5]) for i in range(max(0, len(words) - 4))}


def similarity(a: set[tuple[str, ...]], b: set[tuple[str, ...]]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def audit(output: Path = ART) -> dict:
    manifest = load_json(output / f"{PREFIX}-manifest.json")
    manifest_identity = manifest.pop("manifest_identity")
    require(manifest_identity == sha(canonical(manifest)), "manifest identity")
    require(set(manifest["files"]) == set(LABELS), "file closure")
    rows = {}
    for label in LABELS:
        suffix = ".json" if label == "plan" else ".jsonl"
        path = output / f"{PREFIX}-{label}{suffix}"
        raw = path.read_bytes()
        info = manifest["files"][label]
        require(info["sha256"] == sha(raw) and info["bytes"] == len(raw), f"blob identity: {label}")
        if label != "plan":
            rows[label] = load_rows(path)
            require(info["rows"] == len(rows[label]), f"row count: {label}")
    plan = load_json(output / f"{PREFIX}-plan.json")
    identity = plan.pop("plan_identity")
    require(identity == sha(canonical(plan)), "plan identity")
    require(plan["training_performed"] is False and plan["training_authorized"] is False, "training state")
    require(plan["parent_adapter_identity"] == manifest["parent_adapter_identity"] and
            plan["parent_checkpoint_identity"] == manifest["parent_checkpoint_identity"], "parent binding")
    require((plan["parent_adapter_identity"], plan["parent_checkpoint_identity"]) ==
            (PARENT_ADAPTER, PARENT_CHECKPOINT), "frozen R2 parent")
    require(plan["source_r2_corpus_sha256"] == manifest["source_r2_corpus_sha256"] == source_contract()[2],
            "R2 source closure")
    require(len(rows["train-mechanics"]) == len(rows["train-control"]) ==
            len(rows["replay-baseline"]) == len(rows["replay-protective"]) == 48, "train/replay cardinality")
    require(len(rows["train-mechanics-generic"]) == len(rows["train-control-generic"]) == 48, "generic cardinality")
    require(len(rows["development-requests"]) == len(rows["development-answer-key"]) ==
            len(rows["holdout-requests"]) == len(rows["holdout-answer-key"]) == 24, "eval cardinality")
    require(len(rows["counterexamples"]) == 96, "counterexample cardinality")
    all_cases = {}
    split_families = {}
    for label, split in (("train-mechanics", "TRAIN"), ("development-requests", "DEVELOPMENT"),
                         ("holdout-requests", "INDEPENDENT_HOLDOUT")):
        families = set()
        for row in rows[label]:
            require(row["split"] == split and row["operator"] in OPERATORS, f"split/operator: {label}")
            payload = request(row)
            case_id = row["example_id"]
            require(case_id == payload["case_id"] and case_id not in all_cases, "duplicate/cross-split case")
            core = {k: v for k, v in payload.items() if k != "request_identity"}
            require(payload["request_identity"] == "sha256:" + sha(canonical(core)), "request identity")
            spans = payload["authority_spans"]
            require(len(spans) in (2, 3) and len({s["span_id"] for s in spans}) == len(spans), "source spans")
            require(row["source_family"] not in families, "duplicate source family")
            families.add(row["source_family"])
            all_cases[case_id] = (split, row, payload)
            if split != "TRAIN":
                require(len(row["messages"]) == 2, "answer leaked into eval request")
        split_families[split] = families
        require(Counter(r["operator"] for r in rows[label]) == {op: (6 if split == "TRAIN" else 3) for op in OPERATORS}, "operator balance")
    require(not (split_families["TRAIN"] & split_families["DEVELOPMENT"] |
                 split_families["TRAIN"] & split_families["INDEPENDENT_HOLDOUT"] |
                 split_families["DEVELOPMENT"] & split_families["INDEPENDENT_HOLDOUT"]), "source-family overlap")
    for m, c in zip(rows["train-mechanics"], rows["train-control"]):
        require(m["example_id"] == c["example_id"] and m["messages"][:2] == c["messages"][:2], "paired train input drift")
        require(target(m)["text"] != target(c)["text"], "non-distinct target modes")
    for label in ("train-mechanics", "train-control"):
        for specific, generic in zip(rows[label], rows[label + "-generic"]):
            original, alternate = request(specific), request(generic)
            require(generic["example_id"] == specific["example_id"] + "-generic" and
                    generic["instruction_mode"] == "GENERIC_FACTUAL_REWRITE", "generic identity/mode")
            require(original["authority_spans"] == alternate["authority_spans"] and
                    original["request"] != alternate["request"], "generic source closure")
            require(alternate["request_identity"] == "sha256:" + sha(canonical({k: v for k, v in alternate.items() if k != "request_identity"})),
                    "generic request identity")
            require(target(specific)["text"] == target(generic)["text"] and
                    target(specific)["claim_bindings"] == target(generic)["claim_bindings"], "generic target drift")
            require(target(generic)["request_identity"] == alternate["request_identity"], "generic target binding")
    for label in ("train-mechanics", "train-control"):
        for row in rows[label]:
            value = target(row)
            _, _, payload = all_cases[row["example_id"]]
            require(value["request_identity"] == payload["request_identity"] and value["case_id"] == row["example_id"], "target/request mismatch")
            require(value["outcome"] == "ANSWER" and value["output_type"] == "FACTUAL" and value["abstention_code"] is None, "target outcome")
            require(len(value["text"].encode()) <= 650 and unicodedata.is_normalized("NFC", value["text"]), "text envelope/NFC")
            ids = {s["span_id"] for s in payload["authority_spans"]}
            bindings = value["claim_bindings"]
            require(len(bindings) == 2 and [b["claim_index"] for b in bindings] == [1, 2], "claim structure")
            require(all(set(b["source_span_ids"]) <= ids and b["source_span_ids"] for b in bindings), "claim source binding")
    for split, prefix in (("DEVELOPMENT", "development"), ("INDEPENDENT_HOLDOUT", "holdout")):
        reqs = rows[f"{prefix}-requests"]
        keys = rows[f"{prefix}-answer-key"]
        require([r["example_id"] for r in reqs] == [k["example_id"] for k in keys], "answer key order")
        for row, key in zip(reqs, keys):
            payload = request(row)
            require(key["request_identity"] == payload["request_identity"] and key["operator"] == row["operator"], "answer key binding")
            for mode in ("assistant_target", "control_target"):
                value = json.loads(key[mode])
                require(value["request_identity"] == payload["request_identity"] and value["case_id"] == row["example_id"], "answer key target binding")
                require(tuple(value) == KEY_ORDER, "answer key response schema")
    for negative in rows["counterexamples"]:
        case_id = negative["example_id"]
        require(case_id in all_cases and negative["source_request_identity"] == all_cases[case_id][2]["request_identity"], "negative binding")
        require(negative["negative_text"] and negative["reason_code"] and negative["status"] == "CONTRASTIVE_EVALUATION_ONLY", "negative example")
        split, training_row, _ = all_cases[case_id]
        if split == "TRAIN":
            require(negative["negative_text"] != target(training_row)["text"], "negative entered train target")
    for label in ("replay-baseline", "replay-protective"):
        require(len({sha(canonical(row)) for row in rows[label]}) == 48, "duplicate replay")
        require(all("messages" in row and len(row["messages"]) == 3 for row in rows[label]), "replay target closure")
        source_sets = [set(sha(canonical(row)) for row in load_rows(ART / name)) for name in REPLAY_SOURCES]
        require(all(sha(canonical(row)) in source_sets[i]
                    for i in range(3) for row in rows[label][i * 16:(i + 1) * 16]), "replay provenance")
    baseline_hashes = {sha(canonical(row)) for row in rows["replay-baseline"]}
    protective_hashes = {sha(canonical(row)) for row in rows["replay-protective"]}
    require(baseline_hashes != protective_hashes, "replay ablation has no changed rows")
    factorial = plan["factorial"]
    require(factorial["research_runs"] == 21 and factorial["replicate_seeds"] == [271828, 314159, 161803],
            "ablation runs/seeds")
    expected_arms = {
        "A1": ("LITERAL_SAFE_CONTROL", "OPERATOR_SPECIFIC", "R2_LIKE", "FIXED_BASELINE"),
        "A2": ("NEUTRAL_EDITORIAL_MECHANICS", "OPERATOR_SPECIFIC", "R2_LIKE", "FIXED_BASELINE"),
        "A3": ("LITERAL_SAFE_CONTROL", "OPERATOR_SPECIFIC", "STRONGER_PREDECLARED", "FIXED_BASELINE"),
        "A4": ("NEUTRAL_EDITORIAL_MECHANICS", "OPERATOR_SPECIFIC", "STRONGER_PREDECLARED", "FIXED_BASELINE"),
        "A5": ("NEUTRAL_EDITORIAL_MECHANICS", "OPERATOR_SPECIFIC", "R2_LIKE", "PROTECTIVE_SELECTION"),
        "A6": ("LITERAL_SAFE_CONTROL", "GENERIC_FACTUAL_REWRITE", "R2_LIKE", "FIXED_BASELINE"),
        "A7": ("NEUTRAL_EDITORIAL_MECHANICS", "GENERIC_FACTUAL_REWRITE", "R2_LIKE", "FIXED_BASELINE"),
    }
    require(factorial["arms"][0] == {"id": "A0", "mode": "UNTRAINED_R2_PARENT"} and
            {arm["id"]: (arm["target"], arm["instruction"], arm["recipe"], arm["replay"])
             for arm in factorial["arms"][1:]} == expected_arms and len(factorial["arms"]) == 8,
            "controlled ablation arm projection")
    require(factorial["fixed_training_rows_per_arm"] == 96 and
            factorial["recipe_values"]["R2_LIKE"]["expected_steps"] == 12 and
            factorial["recipe_values"]["STRONGER_PREDECLARED"]["expected_steps"] == 24 and
            factorial["recipe_values"]["R2_LIKE"]["learning_rate"] ==
            factorial["recipe_values"]["STRONGER_PREDECLARED"]["learning_rate"] and
            factorial["common_runtime"]["packing"] is False, "common training variable closure")
    require(plan["evaluation"]["exact_target_string"] == "DIAGNOSTIC_ONLY_NOT_SEMANTIC_VERDICT", "semantic gate")
    require(plan["evaluation"]["safety_priority"] == "ANY_MATERIAL_FACTUAL_OR_EPISTEMIC_REGRESSION_BLOCKS_PARENT_SELECTION" and
            set(plan["evaluation"]["gates"]) == {"FACTUAL_EPISTEMIC_SAFETY", "EDITORIAL_REWRITE_QUALITY",
                                                "ROMANIAN_NATURALNESS", "REGRESSION_PROTECTION"},
            "evaluation contract")
    # Frozen evaluation targets must never enter either new training target mode.
    frozen_targets: set[str] = set()
    for version in ("v1", "r2", "r3", "r4", "r5", "r6"):
        path = ART / f"editor-core-v10-v12-targeted-continuation-{version}-holdout-answer-key.jsonl"
        if path.exists():
            frozen_targets |= {row["assistant_target"] for row in load_rows(path)}
    new_targets = {row["messages"][2]["content"] for label in ("train-mechanics", "train-control", "train-mechanics-generic", "train-control-generic") for row in rows[label]}
    require(not (frozen_targets & new_targets), "frozen holdout target reused")
    references = []
    for path in sorted(ART.glob("*.jsonl")):
        if path.name.startswith(PREFIX):
            continue
        for raw in path.read_bytes().splitlines():
            try:
                row = json.loads(raw)
                if isinstance(row.get("messages"), list) and len(row["messages"]) >= 2 and "\nINPUT=" in row["messages"][1].get("content", ""):
                    references.append((canonical(request(row)), shingles(semantic(row))))
            except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
    bridge = rows["train-mechanics"] + rows["development-requests"] + rows["holdout-requests"]
    maximum_external = 0.0
    external_raw = {raw for raw, _ in references}
    for row in bridge:
        require(canonical(request(row)) not in external_raw, "exact external request contamination")
        tokens = shingles(semantic(row))
        maximum_external = max(maximum_external, *(similarity(tokens, ref) for _, ref in references))
    train_tokens = [shingles(semantic(row)) for row in rows["train-mechanics"]]
    holdout_tokens = [shingles(semantic(row)) for row in rows["holdout-requests"]]
    maximum_internal = max(similarity(a, b) for a in train_tokens for b in holdout_tokens)
    require(maximum_external < 0.72 and maximum_internal < 0.72,
            f"lexical contamination: external={maximum_external:.3f} internal={maximum_internal:.3f}")
    return {"verdict": "PASS", "blockers": 0, "manifest_identity": manifest_identity,
            "plan_identity": identity, "case_count": len(all_cases), "counterexamples": 96,
            "train": 48, "development": 24, "holdout": 24, "replay_each": 48,
            "reference_rows_checked": len(references), "maximum_external_jaccard_5gram": round(maximum_external, 4),
            "maximum_train_holdout_jaccard_5gram": round(maximum_internal, 4),
            "frozen_holdout_targets_reused": False,
            "replay_overlap": len(baseline_hashes & protective_hashes)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    print(json.dumps(audit(args.output_dir), sort_keys=True))
