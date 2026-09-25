from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-factual-setup-r2-causal-diagnostic-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def identity(value: dict, field: str) -> str:
    core = dict(value); expected = core.pop(field)
    actual = hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(actual == expected, f"{field} mismatch")
    return actual


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    protocol = load(f"{PREFIX}-protocol.json")
    manifest = load(f"{PREFIX}-manifest.json")
    recipes = load(f"{PREFIX}-recipes.json")
    evaluation = load(f"{PREFIX}-evaluation.json")
    control = rows(ART / f"{PREFIX}-control-signal.jsonl")
    challenger = rows(ART / f"{PREFIX}-challenger-signal.jsonl")
    source = rows(ART / "editor-core-factual-setup-corrective-v1-training.jsonl")
    benchmark = load("editor-core-factual-setup-benchmark-v1-manifest.json")
    benchmark_requests = rows(ART / "editor-core-factual-setup-benchmark-v1-requests.jsonl")
    benchmark_key = rows(ART / "editor-core-factual-setup-benchmark-v1-answer-key.jsonl")

    identity(protocol, "protocol_identity")
    identity(manifest, "pack_identity")
    identity(recipes, "recipes_identity")
    identity(evaluation, "evaluation_identity")
    require(manifest["protocol_identity"] == protocol["protocol_identity"], "protocol binding")
    require(protocol["parent"] == "R2_STEP_9", "parent")
    require(protocol["real_runs_authorized"] is False and protocol["optimizer_steps_authorized"] == 0, "execution authority")
    require(protocol["fixed_development_manifest_identity"] == benchmark["manifest_identity"], "development binding")
    require(protocol["fixed_evaluation_identity"] == evaluation["evaluation_identity"], "evaluator binding")
    require(protocol["fixed_deterministic_decoding"] == evaluation["deterministic_decoding"], "decoding binding")
    require(evaluation["deterministic_decoding"] == {"do_sample": False, "max_input_tokens": 3072, "max_new_tokens": 2048, "num_beams": 1, "seed": 0, "structural_json_required": True, "temperature": None, "terminal_eos_required": True, "top_p": None}, "deterministic decoding drift")
    require(len(protocol["arms"]) == 4 and all(len(a["runs"]) == 3 for a in protocol["arms"]), "factorial inventory")
    require({tuple(a["seeds"]) for a in protocol["arms"]} == {(161803, 271828, 314159)}, "seed mismatch")
    require(recipes["changed_field_only"] == "learning_rate", "recipe isolation")
    require(recipes["levels"]["S0_CONTROL"]["learning_rate"] == "0.0000005", "control recipe")
    require(recipes["levels"]["S1_HIGHER_PLASTICITY"]["learning_rate"] == "0.0000010", "strong recipe")

    require(len(source) == len(control) == len(challenger) == 72, "row count")
    for src, left, right in zip(source, control, challenger, strict=True):
        require(src["example_id"] == left["example_id"] == right["example_id"], "row order")
        target_hash = hashlib.sha256(src["messages"][-1]["content"].encode()).hexdigest()
        require(left["assistant_target_sha256"] == right["assistant_target_sha256"] == target_hash, "target byte drift")
        if src["split"] == "REPLAY_PROTECTION":
            require(not left["critical_spans"] and not right["critical_spans"], "replay signal drift")
        else:
            require(right["critical_spans"] and right["minimal_pair_id"], "missing challenger signal")
            content = src["messages"][-1]["content"]
            payload = json.loads(content)
            text = payload["text"]
            encoded = json.dumps(text, ensure_ascii=False, separators=(",", ":"))[1:-1]
            text_start = content.index(f'"text":"{encoded}"') + len('"text":"')
            text_end = text_start + len(encoded)
            for span in right["critical_spans"]:
                require(content[span["start"]:span["end"]] == span["text"], "span mutation")
                require(span["field"] == "text" and text_start <= span["start"] < span["end"] <= text_end, "critical span escaped text field")

    pair_counts: dict[str, int] = {}
    for row in challenger:
        if row["minimal_pair_id"]:
            pair_counts[row["minimal_pair_id"]] = pair_counts.get(row["minimal_pair_id"], 0) + 1
    require(len(pair_counts) == 24 and set(pair_counts.values()) == {2}, "minimal pair closure")
    require(manifest["critical_annotated_rows"] == 48, "coverage closure")

    for key, item in manifest["artifacts"].items():
        path = ROOT / item["path"]
        require(path.is_file() and sha(path) == item["sha256"], f"artifact mismatch: {key}")

    train_ids = {r["example_id"] for r in source}
    require(all(not x.startswith("ec-fsc-v1-b-") for x in train_ids), "development id contamination")
    def normalized(value: object) -> str:
        return re.sub(r"\s+", " ", json.dumps(value, ensure_ascii=False, sort_keys=True)).strip().casefold()
    train_messages = {normalized(r["messages"]) for r in source}
    dev_requests = {normalized(r) for r in benchmark_requests}
    dev_keys = {normalized(r) for r in benchmark_key}
    require(not (train_messages & dev_requests) and not (train_messages & dev_keys), "exact normalized train/development contamination")
    require(len(benchmark_requests) == len(benchmark_key) == 24, "development inventory")
    require(evaluation["historical_holdouts_allowed"] is False, "historical holdout boundary")
    require(evaluation["selection_authority"] == "NONE_DEVELOPMENT_RESEARCH_ONLY", "selection authority")
    require(manifest["voice_or_chief_objective"] is False, "objective scope")
    print(json.dumps({"status":"PASS","blockers":0,"protocol_identity":protocol["protocol_identity"],"pack_identity":manifest["pack_identity"],"arms":4,"runs_if_later_authorized":12,"training_rows":72,"development_cases":24,"minimal_pairs":24,"critical_annotated_rows":48,"model_loaded":False,"optimizer_created":False,"training_performed":False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status":"BLOCKED","error":str(exc)}, sort_keys=True), file=sys.stderr)
        raise
