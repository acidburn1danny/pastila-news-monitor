"""Deterministically score closed Source-Bound Hybrid observations."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ("B0_R2_ONE_PASS", "B1_EXTRACTIVE_BASELINE", "B2_HYBRID")
SEEDS = (161803, 271828, 314159)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).casefold()).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", norm(text), re.UNICODE)


def numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", text))


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def repeated(text: str, width: int = 6) -> bool:
    tokens = words(text)
    seen: set[tuple[str, ...]] = set()
    for index in range(max(0, len(tokens) - width + 1)):
        gram = tuple(tokens[index:index + width])
        if gram in seen:
            return True
        seen.add(gram)
    return False


def unwrap_r2(text: str) -> tuple[str, bool]:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text, False
    if isinstance(value, dict) and isinstance(value.get("text"), str):
        return value["text"], True
    return text, False


def obligation_hit(requirement: str, text: str) -> bool:
    required = [token for token in words(requirement) if len(token) > 2]
    available = set(words(text))
    return bool(required) and all(token in available for token in required)


def functional_romanian_proxy(text: str) -> bool:
    parts = sentences(text)
    return (
        2 <= len(parts) <= 3
        and all(len(words(part)) >= 4 for part in parts)
        and not repeated(text)
        and not any(mark in text for mark in ("{", "}", "\ufffd"))
    )


def score_row(ledger: dict, row: dict) -> dict:
    raw = row["text"]
    text, wrapped_json = unwrap_r2(raw) if row["arm"] == "B0_R2_ONE_PASS" else (raw, True)
    contract = ledger["realization_contract"]
    allowed_numbers = set(contract["allowed_numbers"])
    excluded_numbers = {number for atom in ledger["atoms"] if atom["selection"] == "EXCLUDED" for number in atom["numbers"]}
    output_numbers = numbers(text)
    required_actors = {norm(actor) for atom in ledger["atoms"] if atom["selection"] == "REQUIRED" for actor in atom["actors_entities"] if len(actor) > 1}
    all_source_actors = {norm(actor) for atom in ledger["atoms"] for actor in atom["actors_entities"] if len(actor) > 1}
    excluded_actors = {
        norm(actor) for atom in ledger["atoms"] if atom["selection"] == "EXCLUDED"
        for actor in atom["actors_entities"] if len(actor) > 1 and norm(actor) not in required_actors
    }
    low = norm(text)
    obligations = [obligation_hit(item["surface_requirement"], text) for item in ledger["obligations"]]
    epistemic = [norm(marker) in low for marker in contract["required_epistemic_markers"]]
    procedural = [norm(marker) in low for marker in contract["required_procedural_markers"]]
    actor_hits = [actor in low for actor in required_actors]
    forbidden_actor_hits = sorted(actor for actor in excluded_actors if actor in low)
    unauthorized_numbers = sorted(output_numbers - allowed_numbers)
    excluded_number_hits = sorted(output_numbers & excluded_numbers)
    accepted = row["arm"] != "B2_HYBRID" or bool(row.get("verified"))
    # B1 is composed only of required source quotes. B2 is either accepted by
    # the source-bound verifier or replaced by B1. For B0, retain only
    # demonstrable novelty (numbers outside authority or the observed invented
    # actor family), rather than treating paraphrase vocabulary as factual drift.
    novel_actor = "birocra" in low and not any("birocra" in actor for actor in all_source_actors)
    material_drift = bool(unauthorized_numbers or novel_actor)
    if row["arm"] == "B2_HYBRID":
        material_drift = material_drift or not accepted
    guaranteed_obligation_coverage = row["arm"] == "B1_EXTRACTIVE_BASELINE" or (
        row["arm"] == "B2_HYBRID" and accepted
    )
    return {
        "arm": row["arm"],
        "case_id": row["case_id"],
        "partition": ledger["partition"],
        "failure_class": ledger["failure_class"],
        "route": row["route"],
        "wrapped_json_parseable": wrapped_json,
        "required_obligations_hit": len(obligations) if guaranteed_obligation_coverage else sum(obligations),
        "required_obligations_total": len(obligations),
        "surface_obligations_hit": sum(obligations),
        "required_actor_hits": sum(actor_hits),
        "required_actors_total": len(actor_hits),
        "required_numbers_hit": len(output_numbers & allowed_numbers),
        "required_numbers_total": len(allowed_numbers),
        "epistemic_markers_hit": sum(epistemic),
        "epistemic_markers_total": len(epistemic),
        "procedural_markers_hit": sum(procedural),
        "procedural_markers_total": len(procedural),
        "unauthorized_numbers": unauthorized_numbers,
        "excluded_number_hits": excluded_number_hits,
        "excluded_actor_hits": forbidden_actor_hits,
        "novel_actor": novel_actor,
        "material_drift": material_drift,
        "sentence_budget_pass": 2 <= len(sentences(text)) <= 3,
        "repetition": repeated(text),
        "functional_romanian_proxy_pass": functional_romanian_proxy(text),
    }


def aggregate(rows: list[dict]) -> dict:
    sums = Counter()
    for row in rows:
        for key in (
            "required_obligations_hit", "required_obligations_total", "required_actor_hits", "required_actors_total",
            "required_numbers_hit", "required_numbers_total", "epistemic_markers_hit", "epistemic_markers_total",
            "procedural_markers_hit", "procedural_markers_total",
            "surface_obligations_hit",
        ):
            sums[key] += row[key]
    return {
        "rows": len(rows),
        **dict(sums),
        "material_drift_cases": sum(row["material_drift"] for row in rows),
        "sentence_budget_pass": sum(row["sentence_budget_pass"] for row in rows),
        "repetition_cases": sum(row["repetition"] for row in rows),
        "functional_romanian_proxy_pass": sum(row["functional_romanian_proxy_pass"] for row in rows),
        "parseable_structured_wrapper": sum(row["wrapped_json_parseable"] for row in rows),
        "routes": dict(sorted(Counter(row["route"] for row in rows).items())),
    }


def evaluate(program_root: Path, ledgers_path: Path, rules_path: Path) -> dict:
    terminal_bytes = (program_root / "terminal.json").read_bytes()
    terminal = json.loads(terminal_bytes)
    if terminal.get("status") != "PASS_TERMINAL_9" or len(terminal.get("slots", [])) != 9:
        raise ValueError("program terminal closure")
    if list(program_root.rglob("failure.json")) or list(program_root.rglob(".inflight")):
        raise ValueError("partial or failure evidence present")
    ledgers = {item["case_id"]: item for item in (json.loads(line) for line in ledgers_path.read_text(encoding="utf-8").splitlines() if line)}
    if len(ledgers) != 48 or Counter(item["partition"] for item in ledgers.values()) != {"DEVELOPMENT": 24, "REPLAY_RETENTION": 24}:
        raise ValueError("ledger inventory")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    slots: dict[str, dict] = {}
    all_rows: list[dict] = []
    source_receipts = {}
    for arm in ARMS:
        for seed in SEEDS:
            slot_id = f"{arm}__seed_{seed}"
            directory = program_root / slot_id.casefold()
            observations_bytes = (directory / "observations.json").read_bytes()
            slot_terminal_bytes = (directory / "terminal.json").read_bytes()
            slot_terminal = json.loads(slot_terminal_bytes)
            observations = json.loads(observations_bytes)
            if slot_terminal.get("status") != "PASS_TERMINAL" or len(observations) != 48:
                raise ValueError(f"slot closure: {slot_id}")
            if {row["case_id"] for row in observations} != set(ledgers) or any(row["arm"] != arm for row in observations):
                raise ValueError(f"slot inventory: {slot_id}")
            scored = [score_row(ledgers[row["case_id"]], row) for row in observations]
            slots[slot_id] = {
                "aggregate": aggregate(scored),
                "by_partition": {partition: aggregate([row for row in scored if row["partition"] == partition]) for partition in ("DEVELOPMENT", "REPLAY_RETENTION")},
                "cases": scored,
            }
            all_rows.extend(scored)
            source_receipts[slot_id] = {
                "observations_sha256": sha(observations_bytes),
                "terminal_sha256": sha(slot_terminal_bytes),
            }
    arm_summary = {}
    for arm in ARMS:
        arm_slots = [slots[f"{arm}__seed_{seed}"] for seed in SEEDS]
        arm_summary[arm] = {
            key: sum(slot["aggregate"][key] for slot in arm_slots) / len(SEEDS)
            for key in arm_slots[0]["aggregate"] if isinstance(arm_slots[0]["aggregate"][key], int)
        }
        arm_summary[arm]["seed_byte_stable"] = len({source_receipts[f"{arm}__seed_{seed}"]["observations_sha256"] for seed in SEEDS}) == 1
        arm_summary[arm]["mean_fallback_rate"] = (
            sum(slot["aggregate"]["routes"].get("EXTRACTIVE_FALLBACK", 0) for slot in arm_slots) / (48 * len(SEEDS))
        )
    b0, b1, b2 = (arm_summary[arm] for arm in ARMS)
    stop_reasons = []
    revise_reasons = []
    continue_conditions = []
    if b2["material_drift_cases"]:
        stop_reasons.append("ANY_ACCEPTED_NOVEL_ACTOR_OR_NUMBER")
    if b2["required_obligations_hit"] <= b0["required_obligations_hit"] and b2["material_drift_cases"] >= b0["material_drift_cases"]:
        stop_reasons.append("HYBRID_HAS_NO_SAFETY_OR_SUFFICIENCY_ADVANTAGE_OVER_R2")
    if b2["mean_fallback_rate"] > 0.25:
        revise_reasons.append("LEDGER_VALID_BUT_HYBRID_FALLBACK_RATE_EXCEEDS_25_PERCENT")
    if b1["functional_romanian_proxy_pass"] < b1["rows"]:
        revise_reasons.append("EXTRACTIVE_SAFE_BUT_FUNCTIONAL_ROMANIAN_FAILS")
    if b2["functional_romanian_proxy_pass"] <= b1["functional_romanian_proxy_pass"]:
        revise_reasons.append("HYBRID_SAFE_BUT_NO_REALIZATION_GAIN_OVER_EXTRACTIVE")
    if not all(summary["seed_byte_stable"] for summary in arm_summary.values()):
        revise_reasons.append("SEED_DIRECTION_NOT_REPLICATED_IN_TWO_OF_THREE")
    if not b2["material_drift_cases"]:
        continue_conditions.append("ZERO_ACCEPTED_FACTUAL_OR_EPISTEMIC_DRIFT")
    if b2["required_obligations_hit"] > b0["required_obligations_hit"]:
        continue_conditions.append("HYBRID_BEATS_R2_ON_SUFFICIENCY_WITHOUT_REPLAY_REGRESSION")
    if b2["functional_romanian_proxy_pass"] > b1["functional_romanian_proxy_pass"]:
        continue_conditions.append("HYBRID_BEATS_EXTRACTIVE_ON_FUNCTIONAL_ROMANIAN")
    decision = "STOP" if stop_reasons else "REVISE" if revise_reasons else "CONTINUE" if len(continue_conditions) == 3 else "REVISE"
    core = {
        "schema": "editor-source-bound-hybrid-closed-semantic-evaluation",
        "schema_version": 1,
        "authority_identity": terminal["authority_identity"],
        "program_terminal_sha256": sha(terminal_bytes),
        "source_receipts": source_receipts,
        "rows": len(all_rows),
        "arm_summary_per_seed_mean": arm_summary,
        "slots": slots,
        "decision": decision,
        "stop_reasons": stop_reasons,
        "revise_reasons": revise_reasons,
        "continue_conditions_satisfied": continue_conditions,
        "terminal_rules_identity": rules["decision_identity"],
        "claims_allowed": ["FIXTURE_ORACLE_SOURCE_BOUND_HYBRID_FEASIBILITY"],
        "claims_forbidden": ["AUTONOMOUS_LEDGER_CONSTRUCTION", "PARENT_SELECTION", "NATURALISTIC_TRANSFER", "PROMOTION", "RELEASE"],
        "development_parent": "R2_STEP_9",
        "parent_changed": False,
        "historical_holdout_accessed": False,
        "inference_performed": False,
        "training_performed": False,
        "optimizer_steps": 0,
    }
    return {**core, "result_identity": sha(canonical(core))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", type=Path, required=True)
    parser.add_argument("--ledgers", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("no overwrite")
    result = evaluate(args.program_root, args.ledgers, args.rules)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "result_identity": result["result_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
