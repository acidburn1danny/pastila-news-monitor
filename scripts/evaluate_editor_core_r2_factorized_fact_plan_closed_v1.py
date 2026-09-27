"""Evaluate closed factorized fact-plan evidence without model execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

SEEDS = (161803, 271828, 314159)
ARMS = {
    "I0_ONE_PASS_R2": "i0_one_pass_r2",
    "I1_ORACLE_PLAN_SCORE": "i1_oracle_plan_score",
    "I2_ORACLE_PLAN_TO_R2_SETUP": "i2_oracle_plan_to_r2_setup",
}
EXPECTED_FAILURE_SLOT = "I3_R2_PLAN_TO_R2_SETUP__seed_161803"
CONTENT_STOP = {
    "a", "ai", "ale", "al", "au", "ca", "că", "care", "cu", "de", "din",
    "este", "fi", "fost", "iar", "în", "la", "le", "lui", "o", "pe", "pentru",
    "prin", "sau", "se", "și", "un", "unei", "unui",
}
ACTOR_NOUNS = {
    "administrația", "autoritatea", "birocrația", "compania", "consiliul",
    "direcția", "firma", "guvernul", "inspectorii", "ministerul", "operatorul",
    "primăria", "societatea",
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().strip())


def words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+|\d+(?:[.,]\d+)?", normalize(text), re.UNICODE)


def numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", text))


def sentence_count(text: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part])


def has_repetition(text: str, width: int = 6) -> bool:
    tokens = words(text)
    seen: set[tuple[str, ...]] = set()
    for index in range(max(0, len(tokens) - width + 1)):
        gram = tuple(tokens[index : index + width])
        if gram in seen:
            return True
        seen.add(gram)
    return False


def parse_contract_setup(raw: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, ["INVALID_JSON"]
    if not isinstance(payload, dict):
        return None, ["NON_OBJECT_JSON"]
    if not isinstance(payload.get("text"), str) or not payload["text"].strip():
        errors.append("MISSING_CONTRACT_TEXT")
        return None, errors
    text = payload["text"].strip()
    if sentence_count(text) not in (2, 3):
        errors.append("SENTENCE_BUDGET")
    return text, errors


def meaningful_tokens(text: str) -> set[str]:
    return {token for token in words(text) if token not in CONTENT_STOP and len(token) > 2}


def score_setup(raw: str, plan: dict) -> dict:
    text, structural_errors = parse_contract_setup(raw)
    target = plan["oracle_setup_target"]
    requirements = [item["surface_requirement"] for item in plan["selected_facts"]]
    target_numbers = numbers(target)
    source_text = " ".join(item["text"] for item in plan["authority_inventory"])
    source_numbers = numbers(source_text)
    target_actor_terms = {token for token in meaningful_tokens(target) if token in ACTOR_NOUNS}
    source_actor_terms = {token for token in meaningful_tokens(source_text) if token in ACTOR_NOUNS}
    if text is None:
        return {
            "text_extracted": False,
            "contract_valid": False,
            "structural_errors": structural_errors,
            "sentence_budget_pass": False,
            "required_fact_hits": 0,
            "required_fact_total": len(requirements),
            "target_content_hits": 0,
            "target_content_total": len(meaningful_tokens(target)),
            "numeric_hits": 0,
            "numeric_total": len(target_numbers),
            "unsupported_numbers": [],
            "distractor_numbers": [],
            "qualification_hits": 0,
            "qualification_total": len(plan["epistemic_status"]["markers"])
            + len(plan["procedural_status"]["markers"]),
            "novel_actor_terms": [],
            "repetition": False,
            "factual_safety_pass": False,
            "sufficiency_pass": False,
            "functional_romanian_proxy_pass": False,
        }
    normalized = normalize(text)
    output_numbers = numbers(text)
    output_tokens = meaningful_tokens(text)
    target_tokens = meaningful_tokens(target)
    markers = plan["epistemic_status"]["markers"] + plan["procedural_status"]["markers"]
    required_hits = sum(normalize(requirement) in normalized for requirement in requirements)
    qualification_hits = sum(normalize(marker) in normalized for marker in markers)
    output_actor_terms = {token for token in output_tokens if token in ACTOR_NOUNS}
    novel_actor_terms = sorted(output_actor_terms - source_actor_terms - target_actor_terms)
    unsupported_numbers = sorted(output_numbers - source_numbers)
    distractor_numbers = sorted((source_numbers - target_numbers) & output_numbers)
    numeric_hits = len(output_numbers & target_numbers)
    content_hits = len(output_tokens & target_tokens)
    repetition = has_repetition(text)
    sentence_pass = sentence_count(text) in (2, 3)
    factual_safety_pass = not (
        structural_errors
        or unsupported_numbers
        or distractor_numbers
        or novel_actor_terms
        or numeric_hits < len(target_numbers)
        or qualification_hits < len(markers)
        or repetition
    )
    sufficiency_pass = required_hits == len(requirements) and numeric_hits == len(target_numbers)
    return {
        "text_extracted": True,
        "contract_valid": not structural_errors,
        "structural_errors": structural_errors,
        "sentence_budget_pass": sentence_pass,
        "required_fact_hits": required_hits,
        "required_fact_total": len(requirements),
        "target_content_hits": content_hits,
        "target_content_total": len(target_tokens),
        "numeric_hits": numeric_hits,
        "numeric_total": len(target_numbers),
        "unsupported_numbers": unsupported_numbers,
        "distractor_numbers": distractor_numbers,
        "qualification_hits": qualification_hits,
        "qualification_total": len(markers),
        "novel_actor_terms": novel_actor_terms,
        "repetition": repetition,
        "factual_safety_pass": factual_safety_pass,
        "sufficiency_pass": sufficiency_pass,
        "functional_romanian_proxy_pass": sentence_pass and not repetition,
    }


def aggregate(scores: dict[str, dict], cases: dict[str, dict]) -> dict:
    totals: Counter = Counter()
    by_partition: dict[str, Counter] = defaultdict(Counter)
    by_failure_class: dict[str, Counter] = defaultdict(Counter)
    for case_id, score in scores.items():
        groups = (totals, by_partition[cases[case_id]["partition"]], by_failure_class[cases[case_id]["failure_class"]])
        for group in groups:
            group["rows"] += 1
            for key in (
                "text_extracted", "contract_valid", "sentence_budget_pass", "factual_safety_pass",
                "sufficiency_pass", "functional_romanian_proxy_pass", "repetition",
            ):
                group[key] += int(score[key])
            for key in (
                "required_fact_hits", "required_fact_total", "target_content_hits",
                "target_content_total", "numeric_hits", "numeric_total",
                "qualification_hits", "qualification_total",
            ):
                group[key] += score[key]
            group["unsupported_number_cases"] += bool(score["unsupported_numbers"])
            group["distractor_number_cases"] += bool(score["distractor_numbers"])
            group["novel_actor_cases"] += bool(score["novel_actor_terms"])
            for error in score["structural_errors"]:
                group[f"structural_error__{error}"] += 1
    return {
        "overall": dict(totals),
        "by_partition": {key: dict(value) for key, value in sorted(by_partition.items())},
        "by_failure_class": {key: dict(value) for key, value in sorted(by_failure_class.items())},
    }


def delta(i2: dict, i0: dict) -> dict:
    keys = (
        "text_extracted", "contract_valid", "sentence_budget_pass", "factual_safety_pass", "sufficiency_pass",
        "functional_romanian_proxy_pass", "required_fact_hits", "target_content_hits",
        "numeric_hits", "qualification_hits", "unsupported_number_cases",
        "distractor_number_cases", "novel_actor_cases", "repetition",
    )
    return {key: i2.get(key, 0) - i0.get(key, 0) for key in keys}


def verify_terminal(path: Path, expected_slot: str) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt != {
        "optimizer_created": False,
        "rows": 48,
        "slot_id": expected_slot,
        "status": "PASS_TERMINAL",
        "training_performed": False,
    }:
        raise ValueError(f"terminal closure mismatch: {path}")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--oracle-plans", type=Path, required=True)
    parser.add_argument("--evaluation-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite evaluation result")

    cases_rows = read_jsonl(args.cases)
    plan_rows = read_jsonl(args.oracle_plans)
    cases = {row["case_id"]: row for row in cases_rows}
    plans = {row["case_id"]: row for row in plan_rows}
    if len(cases) != 48 or set(cases) != set(plans):
        raise ValueError("case/oracle inventory closure failed")
    contract = json.loads(args.evaluation_contract.read_text(encoding="utf-8"))
    if "PARENT_SELECTION" not in contract.get("claims_forbidden", []):
        raise ValueError("evaluation contract authority drift")

    source_files: dict[str, str] = {
        str(args.cases): sha256_file(args.cases),
        str(args.oracle_plans): sha256_file(args.oracle_plans),
        str(args.evaluation_contract): sha256_file(args.evaluation_contract),
    }
    observations: dict[str, dict[int, list[dict]]] = {arm: {} for arm in ARMS}
    terminals: dict[str, dict[int, dict]] = {arm: {} for arm in ARMS}
    for arm, directory_name in ARMS.items():
        for seed in SEEDS:
            directory = args.run_root / f"{directory_name}__seed_{seed}"
            observation_path = directory / "observations.json"
            terminal_path = directory / "terminal.json"
            rows = json.loads(observation_path.read_text(encoding="utf-8"))
            if len(rows) != 48 or [row["case_id"] for row in rows] != [row["case_id"] for row in cases_rows]:
                raise ValueError(f"row ordering/inventory mismatch: {arm} seed {seed}")
            if any(row.get("intervention") != arm for row in rows):
                raise ValueError(f"intervention crossover: {arm} seed {seed}")
            observations[arm][seed] = rows
            terminals[arm][seed] = verify_terminal(terminal_path, f"{arm}__seed_{seed}")
            source_files[str(observation_path)] = sha256_file(observation_path)
            source_files[str(terminal_path)] = sha256_file(terminal_path)

    failure_path = args.run_root / "failure.json"
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    source_files[str(failure_path)] = sha256_file(failure_path)
    if failure != {
        "error_type": "CalledProcessError",
        "phase": "SLOT_EXECUTION",
        "slot_id": EXPECTED_FAILURE_SLOT,
        "status": "TERMINAL_FAILURE",
    }:
        raise ValueError("I3 terminal failure identity drift")
    i3_directory = args.run_root / "i3_r2_plan_to_r2_setup__seed_161803"
    if i3_directory.exists() and any(i3_directory.iterdir()):
        raise ValueError("I3 partial eligible evidence exists")

    setup_results: dict[str, dict[str, dict]] = {"I0_ONE_PASS_R2": {}, "I2_ORACLE_PLAN_TO_R2_SETUP": {}}
    setup_aggregates: dict[str, dict[str, dict]] = {"I0_ONE_PASS_R2": {}, "I2_ORACLE_PLAN_TO_R2_SETUP": {}}
    for arm in setup_results:
        for seed in SEEDS:
            scored = {row["case_id"]: score_setup(row["setup"], plans[row["case_id"]]) for row in observations[arm][seed]}
            setup_results[arm][str(seed)] = scored
            setup_aggregates[arm][str(seed)] = aggregate(scored, cases)

    per_seed_comparison = {}
    seed_directions = []
    for seed in SEEDS:
        i0 = setup_aggregates["I0_ONE_PASS_R2"][str(seed)]["overall"]
        i2 = setup_aggregates["I2_ORACLE_PLAN_TO_R2_SETUP"][str(seed)]["overall"]
        per_case = Counter()
        for case_id in cases:
            left = setup_results["I0_ONE_PASS_R2"][str(seed)][case_id]
            right = setup_results["I2_ORACLE_PLAN_TO_R2_SETUP"][str(seed)][case_id]
            left_tuple = (left["factual_safety_pass"], left["sufficiency_pass"], left["contract_valid"])
            right_tuple = (right["factual_safety_pass"], right["sufficiency_pass"], right["contract_valid"])
            if right_tuple > left_tuple:
                per_case["I2_WIN"] += 1
            elif right_tuple < left_tuple:
                per_case["I0_WIN"] += 1
            else:
                per_case["TIE"] += 1
        critical_no_regression = all(
            i2[key] >= i0[key]
            for key in ("text_extracted", "factual_safety_pass", "required_fact_hits", "numeric_hits")
        )
        critical_gain = any(
            i2[key] > i0[key]
            for key in ("factual_safety_pass", "sufficiency_pass", "qualification_hits")
        )
        direction = "I2_ADVANTAGE" if critical_no_regression and critical_gain else (
            "MIXED_WITH_MATERIAL_REGRESSION" if not critical_no_regression else "TIE"
        )
        seed_directions.append(direction)
        per_seed_comparison[str(seed)] = {
            "aggregate_delta_i2_minus_i0": delta(i2, i0),
            "case_winners": dict(per_case),
            "direction": direction,
        }

    i1_results: dict[str, dict] = {}
    for seed in SEEDS:
        nlls: list[float] = []
        identity_matches = 0
        finite = 0
        by_partition: dict[str, list[float]] = defaultdict(list)
        by_failure_class: dict[str, list[float]] = defaultdict(list)
        for row in observations["I1_ORACLE_PLAN_SCORE"][seed]:
            case_id = row["case_id"]
            nll = row.get("teacher_forced_nll")
            if isinstance(nll, (int, float)) and math.isfinite(nll):
                finite += 1
                nlls.append(float(nll))
                by_partition[cases[case_id]["partition"]].append(float(nll))
                by_failure_class[cases[case_id]["failure_class"]].append(float(nll))
            identity_matches += row.get("plan_identity") == plans[case_id]["plan_identity"]
        i1_results[str(seed)] = {
            "rows": 48,
            "finite_nll": finite,
            "plan_identity_matches": identity_matches,
            "nll_mean": statistics.fmean(nlls),
            "nll_median": statistics.median(nlls),
            "nll_min": min(nlls),
            "nll_max": max(nlls),
            "partition_mean": {key: statistics.fmean(value) for key, value in sorted(by_partition.items())},
            "failure_class_mean": {key: statistics.fmean(value) for key, value in sorted(by_failure_class.items())},
        }

    i2_advantage_seeds = sum(direction == "I2_ADVANTAGE" for direction in seed_directions)
    i2_regression_seeds = sum(direction == "MIXED_WITH_MATERIAL_REGRESSION" for direction in seed_directions)
    i1_operationally_scorable = all(
        value["finite_nll"] == 48 and value["plan_identity_matches"] == 48 for value in i1_results.values()
    )
    if i2_advantage_seeds >= 2:
        decision = "REVISE_STRUCTURAL_PLAN_DECODING"
        bottleneck = "PLAN_CONSTRUCTION"
        i3_interpretation = "I3 supports a bounded structural-decoding successor because oracle plans improve realization."
    else:
        decision = "STOP_FACTORIZED_DIRECTION_V1"
        bottleneck = "PLAN_TO_TEXT_REALIZATION_AND_CONTRACT_ADHERENCE; PLAN_CONSTRUCTION_EFFECT_NOT_IDENTIFIABLE_FROM_I3"
        i3_interpretation = (
            "I3 proves a structural plan-generation failure for one case/seed, but without an I2 advantage it does not "
            "justify spending another run on structural JSON decoding."
        )

    core = {
        "schema": "editor-r2-factorized-fact-plan-closed-deterministic-evaluation",
        "schema_version": 1,
        "evaluation_mode": "CLOSED_EVIDENCE_ONLY_NO_INFERENCE",
        "source_files_sha256": source_files,
        "closed_rows": 432,
        "eligible_intervention_slots": 9,
        "i3_terminal_failure": failure,
        "i3_partial_eligible_evidence": False,
        "setup_aggregates": setup_aggregates,
        "i2_vs_i0_per_seed": per_seed_comparison,
        "seed_directions": seed_directions,
        "i2_advantage_seeds": i2_advantage_seeds,
        "i2_regression_seeds": i2_regression_seeds,
        "i1_oracle_plan_score": i1_results,
        "i1_operationally_scorable": i1_operationally_scorable,
        "i1_claim_limit": "Finite teacher-forced likelihood proves scoreability, not autonomous plan construction validity.",
        "dominant_bottleneck": bottleneck,
        "i3_interpretation": i3_interpretation,
        "decision": decision,
        "decision_basis": {
            "oracle_plan_advantage_required_in_at_least_two_seeds": True,
            "observed_i2_advantage_seeds": i2_advantage_seeds,
            "observed_i2_regression_seeds": i2_regression_seeds,
            "structural_decoder_successor_authorized_by_evidence": i2_advantage_seeds >= 2,
        },
        "development_parent": "R2_STEP_9",
        "development_parent_changed": False,
        "parent_selection_authority": False,
        "historical_holdout_accessed": False,
        "new_inference_performed": False,
        "slots_rerun": 0,
        "training_performed": False,
        "optimizer_steps": 0,
        "claims_allowed": [
            "CLOSED_DEVELOPMENT_DIAGNOSTIC_I2_VS_I0",
            "ORACLE_PLAN_TEACHER_FORCED_SCOREABILITY",
            "I3_STRUCTURAL_FAILURE_OBSERVED_ONE_CASE_ONE_SEED",
        ],
        "claims_forbidden": [
            "PARENT_SELECTION", "NATURALISTIC_TRANSFER", "HISTORICAL_HOLDOUT_RESULT", "PROMOTION", "RELEASE",
        ],
    }
    result = {**core, "result_identity": sha256_bytes(canonical(core))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": decision,
        "i1_operationally_scorable": i1_operationally_scorable,
        "i2_advantage_seeds": i2_advantage_seeds,
        "i2_regression_seeds": i2_regression_seeds,
        "result_identity": result["result_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
