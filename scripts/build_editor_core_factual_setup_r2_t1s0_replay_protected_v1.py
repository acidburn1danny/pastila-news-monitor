from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
SOURCE = ART / "editor-core-factual-setup-corrective-v1-training.jsonl"
CONTROL = ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl"
RECIPES = ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-recipes.json"
EVALUATION = ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-evaluation.json"
TERMINAL = ART / "editor-core-factual-setup-r2-causal-diagnostic-terminal-result-v1.json"
PREFIX = "editor-core-factual-setup-r2-t1s0-replay-protected-v1"
SEEDS = [161803, 271828, 314159]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(value: dict, field: str) -> dict:
    core = dict(value)
    core.pop(field, None)
    digest = hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**core, field: digest}


def write_json(path: Path, value: dict) -> None:
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode())


def text_span(content: str) -> dict:
    payload = json.loads(content)
    text = payload["text"]
    encoded = json.dumps(text, ensure_ascii=False, separators=(",", ":"))[1:-1]
    marker = f'"text":"{encoded}"'
    start = content.find(marker)
    if start < 0:
        raise ValueError("assistant text is not byte-addressable")
    start += len('"text":"')
    if content[start : start + len(text)] != text:
        raise ValueError("text span mismatch")
    return {"field": "text", "start": start, "end": start + len(text), "text": text}


def main() -> None:
    source = [json.loads(line) for line in SOURCE.read_text("utf-8").splitlines() if line.strip()]
    control = [json.loads(line) for line in CONTROL.read_text("utf-8").splitlines() if line.strip()]
    recipes = json.loads(RECIPES.read_text("utf-8"))
    evaluation = json.loads(EVALUATION.read_text("utf-8"))
    terminal = json.loads(TERMINAL.read_text("utf-8"))
    by_id = {row["example_id"]: row for row in source}
    if len(source) != 72 or len(control) != 72 or len(by_id) != 72:
        raise ValueError("frozen corpus/control cardinality")

    protected: list[dict] = []
    coverage: dict[str, int] = {}
    for old in control:
        row = by_id[old["example_id"]]
        if hashlib.sha256(row["messages"][-1]["content"].encode()).hexdigest() != old["assistant_target_sha256"]:
            raise ValueError("assistant target identity drift")
        if old["split"] == "CORRECTIVE_TARGETED":
            protected.append(old)
            continue
        if old["split"] != "REPLAY_PROTECTION":
            raise ValueError("unknown split")
        span = text_span(row["messages"][-1]["content"])
        protection = {
            "INCOMPLETE_PROCEDURAL_STATUS": "PROCEDURAL_STATUS",
            "INCOMPLETE_NUMERIC_RECONCILIATION": "NUMERIC_RECONCILIATION",
            "INVENTED_ACTOR": "ACTOR_FIDELITY",
            "ENTITY_SUBSTITUTION": "ACTOR_FIDELITY",
            "CATEGORICAL_ALLEGATION": "EPISTEMIC_QUALIFICATION",
            "LOST_QUALIFICATION": "EPISTEMIC_QUALIFICATION",
        }[old["failure_class"]]
        coverage[protection] = coverage.get(protection, 0) + 1
        protected.append({
            **old,
            "signal": "CONTRACT_CRITICAL_SPAN_WEIGHTED_REPLAY_PROTECTION",
            "critical_weight": "3.0",
            "critical_spans": [span],
            "replay_protection": protection,
            "anti_repetition_basis": "COMPLETE_NON_REPETITIVE_EDITORIAL_TEXT_SEQUENCE",
        })

    signal_path = ART / f"{PREFIX}-protected-signal.jsonl"
    write_jsonl(signal_path, protected)
    arms = [
        {"arm_id": "T1_S0_EXISTING_CONTROL", "signal_sha256": sha(CONTROL)},
        {"arm_id": "T1_S0_REPLAY_PROTECTED", "signal_sha256": sha(signal_path)},
    ]
    protocol = identity({
        "schema": "editor-factual-setup-r2-t1s0-replay-protected-protocol",
        "schema_version": 1,
        "status": "DESIGN_ONLY_REAL_RUNS_NOT_AUTHORIZED",
        "parent": "R2_STEP_9",
        "parent_adapter_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        "source_terminal_result_identity": terminal["result_identity"],
        "hypothesis": "T1_S0_WITH_EXPLICIT_REPLAY_WEIGHTING_RETAINS_TARGETED_GAIN_WITHOUT_PROCEDURAL_NUMERIC_ACTOR_OR_REPETITION_REGRESSION",
        "arms": arms,
        "seeds": SEEDS,
        "matched_row_order_per_seed": True,
        "fixed": {
            "training_corpus_sha256": sha(SOURCE),
            "recipe_level": "S0_CONTROL",
            "recipe_identity": recipes["recipes_identity"],
            "learning_rate": recipes["levels"]["S0_CONTROL"]["learning_rate"],
            "evaluator_identity": evaluation["evaluation_identity"],
            "deterministic_decoding": evaluation["deterministic_decoding"],
            "assistant_target_bytes": "IDENTICAL_ALL_72_ROWS",
            "corrective_signal_rows": "BYTE_IDENTICAL_ALL_48_ROWS",
        },
        "single_causal_difference": "CRITICAL_SPAN_WEIGHTING_ADDED_TO_24_REPLAY_TEXT_VALUES",
        "replay_protections": {
            "procedural_status": "weight the complete safe procedural sequence",
            "numeric_reconciliation": "weight the complete reconciled numeric sequence",
            "actor_fidelity": "weight the complete actor-bound sequence",
            "repetition_degeneration": "weight complete non-repetitive 2-3 sentence text and score repetition identically in both arms",
            "epistemic_qualification": "retain existing allegation and qualification replay safety",
        },
        "common_repetition_gate": {
            "applies_identically_to_both_arms": True,
            "normalized_duplicate_sentence_allowed": False,
            "normalized_repeated_clause_allowed": False,
            "novel_actor_allowed": False,
            "material_replay_regressions_allowed": 0,
        },
        "measurements": [
            "TEACHER_FORCED_FULL_TARGET_NLL",
            "TEACHER_FORCED_REPLAY_CRITICAL_SPAN_NLL",
            "DETERMINISTIC_DEVELOPMENT_SEMANTIC_SCORE",
            "DETERMINISTIC_REPLAY_RETENTION",
            "PROCEDURAL_NUMERIC_ACTOR_AND_REPETITION_FAILURE_COUNTS",
            "ADAPTER_DELTA",
            "BETWEEN_SEED_STABILITY",
        ],
        "decision_table": {
            "STOP": "ANY_MATERIAL_FACTUAL_EPISTEMIC_OR_REPLAY_REGRESSION_OR_NO_REPLICATED_DEVELOPMENT_SIGNAL",
            "REVISE": "REPLAY_PROTECTION_IMPROVES_RETENTION_BUT_ERASES_TARGETED_DEVELOPMENT_GAIN",
            "CONTINUE_RESEARCH": "PROTECTED_ARM_PRESERVES_T1_S0_DEVELOPMENT_SIGNAL_AND_HAS_ZERO_MATERIAL_REPLAY_REGRESSIONS_IN_AT_LEAST_2_OF_3_SEEDS",
        },
        "claims_allowed": ["CAUSAL_EFFECT_OF_EXPLICIT_REPLAY_WEIGHTING_UNDER_T1_S0"],
        "claims_forbidden": ["PARENT_SELECTION", "NATURALISTIC_TRANSFER", "PROMOTION", "RELEASE"],
        "historical_holdouts_allowed": False,
        "real_runs_authorized": False,
        "model_load_authorized": False,
        "optimizer_creation_authorized": False,
        "optimizer_steps_authorized": 0,
        "training_authorized": False,
        "parent_selection_authority": False,
    }, "protocol_identity")
    protocol_path = ART / f"{PREFIX}-protocol.json"
    write_json(protocol_path, protocol)

    manifest = identity({
        "schema": "editor-factual-setup-r2-t1s0-replay-protected-pack",
        "schema_version": 1,
        "protocol_identity": protocol["protocol_identity"],
        "source_training_sha256": sha(SOURCE),
        "control_signal_sha256": sha(CONTROL),
        "protected_signal_sha256": sha(signal_path),
        "recipes_identity": recipes["recipes_identity"],
        "evaluation_identity": evaluation["evaluation_identity"],
        "rows": 72,
        "corrective_rows_unchanged": 48,
        "replay_rows_protected": 24,
        "coverage": coverage,
        "assistant_target_bytes_identical": True,
        "historical_holdouts_read": False,
        "voice_or_chief_objective": False,
    }, "pack_identity")
    write_json(ART / f"{PREFIX}-manifest.json", manifest)


if __name__ == "__main__":
    main()
