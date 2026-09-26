"""Score the closed T1/S0 replay-protected development/replay experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


EXPECTED = (
    "R2_STEP_9",
    "T1_S0_EXISTING_CONTROL__seed_161803",
    "T1_S0_EXISTING_CONTROL__seed_271828",
    "T1_S0_EXISTING_CONTROL__seed_314159",
    "T1_S0_REPLAY_PROTECTED__seed_161803",
    "T1_S0_REPLAY_PROTECTED__seed_271828",
    "T1_S0_REPLAY_PROTECTED__seed_314159",
)
SEEDS = (161803, 271828, 314159)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def normalized_sentences(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", item.strip().casefold()) for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]


def has_repeated_clause(text: str, width: int = 6) -> bool:
    tokens = re.findall(r"[\wăâîșț]+", text.casefold())
    seen: dict[tuple[str, ...], int] = {}
    for index in range(len(tokens) - width + 1):
        gram = tuple(tokens[index : index + width])
        if gram in seen and index - seen[gram] >= width:
            return True
        seen.setdefault(gram, index)
    return False


def score(root: Path, requests_path: Path) -> dict:
    program = json.loads((root / "program-terminal.json").read_text(encoding="utf-8"))
    if program["status"] != "PASS_7_DEVELOPMENT_REPLAY_BUNDLES" or program["rows"] != 336 or program["terminal_eos"] != 336:
        raise ValueError("inference closure")
    if program["answer_key_accessed"] or program["historical_holdout_accessed"] or program["optimizer_steps"]:
        raise ValueError("inference isolation")

    requests = {row["example_id"]: row for row in read_jsonl(requests_path)}
    if len(requests) != 48 or any(any(message["role"] == "assistant" for message in row["messages"]) for row in requests.values()):
        raise ValueError("request isolation")

    bundles: dict[str, dict[str, dict]] = {}
    receipts = {}
    for candidate in EXPECTED:
        directory = root / candidate
        receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
        response_bytes = (directory / "responses.jsonl").read_bytes()
        observation_bytes = (directory / "observations.jsonl").read_bytes()
        if receipt["candidate_id"] != candidate or receipt["rows"] != 48 or receipt["terminal_eos"] != 48:
            raise ValueError("candidate closure")
        receipt_core = {key: value for key, value in receipt.items() if key != "receipt_identity"}
        if receipt.get("receipt_identity") != sha(canonical(receipt_core)):
            raise ValueError("receipt identity")
        if receipt["responses_sha256"] != sha(response_bytes) or receipt["observations_sha256"] != sha(observation_bytes):
            raise ValueError("candidate identity")
        rows = read_jsonl(directory / "responses.jsonl")
        if {row["case_id"] for row in rows} != set(requests):
            raise ValueError("candidate inventory")
        bundles[candidate] = {row["case_id"]: {**row, "parsed": json.loads(row["response"])} for row in rows}
        receipts[candidate] = receipt["receipt_identity"]
    if program["receipts"] != [receipts[candidate] for candidate in EXPECTED]:
        raise ValueError("program receipt binding")

    parent = bundles["R2_STEP_9"]
    metrics = {}
    findings = []
    for candidate in EXPECTED:
        rows = bundles[candidate]
        dev = [case for case, row in rows.items() if row["split"] == "INDEPENDENT_SELECTION_BENCHMARK"]
        replay = [case for case, row in rows.items() if row["split"] == "REPLAY_RETENTION"]
        if len(dev) != 24 or len(replay) != 24:
            raise ValueError("partition inventory")
        duplicates = []
        repeated_clauses = []
        for case, row in rows.items():
            sentences = normalized_sentences(row["parsed"]["text"])
            if len(sentences) != len(set(sentences)):
                duplicates.append(case)
            if has_repeated_clause(row["parsed"]["text"]):
                repeated_clauses.append(case)
        metrics[candidate] = {
            "development_parent_equal": sum(rows[case]["response"] == parent[case]["response"] for case in dev),
            "development_rows": len(dev),
            "replay_parent_equal": sum(rows[case]["response"] == parent[case]["response"] for case in replay),
            "replay_rows": len(replay),
            "normalized_duplicate_sentence_cases": duplicates,
            "normalized_repeated_clause_cases": repeated_clauses,
        }

    protected = [f"T1_S0_REPLAY_PROTECTED__seed_{seed}" for seed in SEEDS]
    control = [f"T1_S0_EXISTING_CONTROL__seed_{seed}" for seed in SEEDS]
    for candidate in control + protected:
        # Replicated, source-bound development gain: R2 omitted the alert's object.
        case = "ec-editor-setup-v1-03"
        text = bundles[candidate][case]["parsed"]["text"].casefold()
        parent_text = parent[case]["parsed"]["text"].casefold()
        if "conduct" in text and "conduct" not in parent_text:
            findings.append({"candidate_id": candidate, "case_id": case, "split": "DEVELOPMENT", "finding": "SOURCE_BOUND_SUFFICIENCY_GAIN", "materiality": "POSITIVE"})

        # Material replay regression: R2 preserves all three reconciled numbers;
        # every trained adapter drops the duplicate count 391.
        case = "ec-fsc-v1-r-5-01"
        text = bundles[candidate][case]["parsed"]["text"]
        parent_text = parent[case]["parsed"]["text"]
        if "391" not in text and "391" in parent_text:
            findings.append({"candidate_id": candidate, "case_id": case, "split": "REPLAY", "finding": "MATERIAL_NUMERIC_RECONCILIATION_REGRESSION", "materiality": "MATERIAL"})

        # Absolute common gate: the authority contains no actor named Birocratia.
        for case in ("ec-fsc-v1-r-6-01", "ec-fsc-v1-r-6-02", "ec-fsc-v1-r-6-03", "ec-fsc-v1-r-6-04"):
            text = bundles[candidate][case]["parsed"]["text"].casefold()
            payload = json.loads(requests[case]["messages"][1]["content"].split("\nINPUT=", 1)[1])
            authority = " ".join(span["text"] for span in payload["authority_spans"]).casefold()
            if "birocra" in text and "birocra" not in authority:
                findings.append({"candidate_id": candidate, "case_id": case, "split": "REPLAY", "finding": "NOVEL_ACTOR", "materiality": "MATERIAL"})

    protected_summary = {}
    for seed, candidate in zip(SEEDS, protected):
        own = [item for item in findings if item["candidate_id"] == candidate]
        protected_summary[str(seed)] = {
            "development_gains": sum(item["materiality"] == "POSITIVE" for item in own),
            "material_replay_regressions": sum(item["finding"].endswith("REGRESSION") for item in own),
            "novel_actor_cases": sum(item["finding"] == "NOVEL_ACTOR" for item in own),
            "duplicate_sentence_cases": metrics[candidate]["normalized_duplicate_sentence_cases"],
            "repeated_clause_cases": metrics[candidate]["normalized_repeated_clause_cases"],
        }

    replicated_gain = all(protected_summary[str(seed)]["development_gains"] >= 1 for seed in SEEDS)
    zero_material_replay_regressions = all(protected_summary[str(seed)]["material_replay_regressions"] == 0 for seed in SEEDS)
    common_gate = all(
        protected_summary[str(seed)]["novel_actor_cases"] == 0
        and not protected_summary[str(seed)]["duplicate_sentence_cases"]
        and not protected_summary[str(seed)]["repeated_clause_cases"]
        for seed in SEEDS
    )
    decision = "CONTINUE_RESEARCH" if replicated_gain and zero_material_replay_regressions and common_gate else "STOP"
    reasons = []
    if not zero_material_replay_regressions:
        reasons.append("MATERIAL_REPLAY_REGRESSION")
    if not common_gate:
        reasons.append("COMMON_NOVEL_ACTOR_OR_REPETITION_GATE_FAILED")
    if not replicated_gain:
        reasons.append("NO_REPLICATED_DEVELOPMENT_SIGNAL")

    core = {
        "schema": "editor-factual-setup-r2-t1s0-replay-protected-deterministic-evaluation",
        "schema_version": 1,
        "inference_program_identity": sha(canonical(program)),
        "source_receipts": receipts,
        "rows": 336,
        "terminal_eos": 336,
        "metrics": metrics,
        "protected_seed_summary": protected_summary,
        "findings": findings,
        "replicated_development_signal": replicated_gain,
        "zero_material_replay_regressions": zero_material_replay_regressions,
        "common_repetition_actor_gate_pass": common_gate,
        "decision": decision,
        "decision_reasons": reasons,
        "claims_allowed": ["CAUSAL_EFFECT_OF_EXPLICIT_REPLAY_WEIGHTING_UNDER_T1_S0"],
        "claims_forbidden": ["PARENT_SELECTION", "NATURALISTIC_TRANSFER", "PROMOTION", "RELEASE"],
        "development_parent": "R2_STEP_9",
        "parent_changed": False,
        "historical_holdout_accessed": False,
        "training_performed": False,
        "optimizer_steps": 0,
    }
    return {**core, "result_identity": sha(canonical(core))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("no overwrite")
    result = score(args.evaluation_root, args.requests)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "result_identity": result["result_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
