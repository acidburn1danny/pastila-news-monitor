from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
SOURCE = ART / "editor-core-factual-setup-corrective-v1-training.jsonl"
BENCHMARK = ART / "editor-core-factual-setup-benchmark-v1-manifest.json"
CONTRACT = ART / "editor-core-factual-setup-contract-v1.json"
PREFIX = "editor-core-factual-setup-r2-causal-diagnostic-v1"
SEEDS = [161803, 271828, 314159]
PARENT_ADAPTER = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
PARENT_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"

CRITICAL_TERMS = {
    "INVENTED_ACTOR": ["Consiliul local", "Direcția tehnică", "nu a fost încă semnat", "ar urma"],
    "ENTITY_SUBSTITUTION": ["Operatorul Entitatea", "utilizatori", "estimează"],
    "CATEGORICAL_ALLEGATION": ["raport preliminar", "susține", "ar fi", "contestată", "nu sunt stabilite"],
    "LOST_QUALIFICATION": ["estimează", "numai dacă", "poate fi revizuită"],
    "INCOMPLETE_NUMERIC_RECONCILIATION": ["provizoriu", "duplicate", "corectat", "distincte"],
    "INCOMPLETE_PROCEDURAL_STATUS": ["a propus", "urmează să voteze", "nu există o decizie finală", "rămâne în vigoare"],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(obj: dict, field: str) -> dict:
    core = dict(obj)
    core.pop(field, None)
    digest = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**core, field: digest}


def write_json(path: Path, value: dict) -> None:
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes("".join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for r in rows).encode("utf-8"))


def occurrence_spans(content: str, terms: list[str]) -> list[dict]:
    payload = json.loads(content)
    text = payload["text"]
    encoded = json.dumps(text, ensure_ascii=False, separators=(",", ":"))[1:-1]
    marker = f'"text":"{encoded}"'
    marker_start = content.find(marker)
    if marker_start < 0:
        raise ValueError("assistant text field is not byte-addressable")
    text_start = marker_start + len('"text":"')
    spans: list[dict] = []
    for term in terms:
        for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            spans.append({"start": text_start + match.start(), "end": text_start + match.end(), "text": match.group(0), "field": "text"})
    for match in re.finditer(r"(?<![A-Za-z_])\d+(?:[.,]\d+)?%?", text):
        spans.append({"start": text_start + match.start(), "end": text_start + match.end(), "text": match.group(0), "field": "text"})
    unique = {(x["start"], x["end"]): x for x in spans}
    return [unique[k] for k in sorted(unique)]


def main() -> None:
    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    targeted = [r for r in rows if r["split"] == "CORRECTIVE_TARGETED"]
    replay = [r for r in rows if r["split"] == "REPLAY_PROTECTION"]

    control: list[dict] = []
    challenger: list[dict] = []
    grouped: dict[str, list[dict]] = {}
    for row in targeted:
        grouped.setdefault(row["failure_class"], []).append(row)

    pair_for: dict[str, str] = {}
    for failure_class, items in sorted(grouped.items()):
        items.sort(key=lambda r: r["example_id"])
        for offset in range(0, len(items), 2):
            pair_id = f"{failure_class.lower()}-pair-{offset // 2 + 1:02d}"
            for item in items[offset:offset + 2]:
                pair_for[item["example_id"]] = pair_id

    for row in rows:
        assistant = row["messages"][-1]["content"]
        common = {
            "example_id": row["example_id"],
            "failure_class": row["failure_class"],
            "split": row["split"],
            "assistant_target_sha256": hashlib.sha256(assistant.encode()).hexdigest(),
            "minimal_pair_id": pair_for.get(row["example_id"]),
        }
        control.append({**common, "signal": "UNIFORM_ASSISTANT_TOKEN_LOSS", "base_weight": "1.0", "critical_spans": []})
        spans = occurrence_spans(assistant, CRITICAL_TERMS[row["failure_class"]]) if row["split"] == "CORRECTIVE_TARGETED" else []
        challenger.append({
            **common,
            "signal": "CONTRACT_CRITICAL_SPAN_WEIGHTED_LOSS" if spans else "UNIFORM_REPLAY_PROTECTION_LOSS",
            "base_weight": "1.0",
            "critical_weight": "3.0" if spans else "1.0",
            "critical_spans": spans,
        })

    control_path = ART / f"{PREFIX}-control-signal.jsonl"
    challenger_path = ART / f"{PREFIX}-challenger-signal.jsonl"
    write_jsonl(control_path, control)
    write_jsonl(challenger_path, challenger)

    recipes = sealed({
        "schema": "editor-factual-setup-r2-causal-diagnostic-recipes",
        "schema_version": 1,
        "fixed": {
            "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE",
            "scheduler": "CONSTANT_WITHOUT_WARMUP",
            "epochs": 1,
            "micro_batch_size": 1,
            "gradient_accumulation_steps": 8,
            "optimizer_steps": 9,
            "max_sequence_tokens": 3072,
            "precision": "BF16",
            "packing": False,
            "assistant_only_loss": True,
        },
        "levels": {
            "S0_CONTROL": {"learning_rate": "0.0000005"},
            "S1_HIGHER_PLASTICITY": {"learning_rate": "0.0000010"},
        },
        "changed_field_only": "learning_rate",
    }, "recipes_identity")
    recipes_path = ART / f"{PREFIX}-recipes.json"
    write_json(recipes_path, recipes)

    evaluation = sealed({
        "schema": "editor-factual-setup-r2-causal-diagnostic-evaluation",
        "schema_version": 1,
        "development_manifest_identity": benchmark["manifest_identity"],
        "development_cases": benchmark["cases"],
        "development_requests_sha256": benchmark["requests_sha256"],
        "development_answer_key_sha256": benchmark["answer_key_sha256"],
        "historical_holdouts_allowed": False,
        "metrics": {
            "teacher_forced": ["FULL_ASSISTANT_MEAN_NLL", "CRITICAL_SPAN_MEAN_NLL", "CRITICAL_TOKEN_COVERAGE"],
            "acquisition": ["TRAIN_DECODE_SEMANTIC_PASS", "TRAIN_CRITICAL_UNIT_RECALL"],
            "generalization": ["DEVELOPMENT_PAIRED_SEMANTIC_WIN", "DEVELOPMENT_CRITICAL_UNIT_RECALL"],
            "safety": ["FACTUAL_ERROR", "EPISTEMIC_ERROR", "INVENTED_ACTOR_OR_ENTITY"],
            "retention": ["REPLAY_SEMANTIC_PASS", "REPLAY_REGRESSION"],
            "behavior": ["DETERMINISTIC_RESPONSE_SHA256", "PARENT_EQUAL_RESPONSE_COUNT"],
            "adapter": ["FULL_ADAPTER_CONTENT_IDENTITY", "L2_DELTA_BY_TENSOR", "CHANGED_TENSOR_COUNT"],
            "stability": ["PER_SEED_DIRECTION", "SEED_AGREEMENT"],
        },
        "deterministic_decoding": {
            "do_sample": False,
            "num_beams": 1,
            "temperature": None,
            "top_p": None,
            "seed": 0,
            "max_input_tokens": 3072,
            "max_new_tokens": 2048,
            "terminal_eos_required": True,
            "structural_json_required": True,
        },
        "selection_authority": "NONE_DEVELOPMENT_RESEARCH_ONLY",
        "exact_target_match_is_not_semantic_verdict": True,
    }, "evaluation_identity")
    evaluation_path = ART / f"{PREFIX}-evaluation.json"
    write_json(evaluation_path, evaluation)

    arms = []
    for signal in ("T0_CONTROL", "T1_CONTRACT_WEIGHTED"):
        for strength in ("S0_CONTROL", "S1_HIGHER_PLASTICITY"):
            arm_id = f"{signal}_{strength}"
            arms.append({
                "arm_id": arm_id,
                "target_signal": signal,
                "signal_sha256": sha(control_path if signal == "T0_CONTROL" else challenger_path),
                "recipe_strength": strength,
                "seeds": SEEDS,
                "runs": [f"{arm_id}__seed_{seed}" for seed in SEEDS],
            })

    protocol = sealed({
        "schema": "editor-factual-setup-r2-causal-learnability-stability-protocol",
        "schema_version": 1,
        "status": "DESIGN_ONLY_REAL_RUNS_NOT_AUTHORIZED",
        "contract_identity": contract["contract_identity"],
        "parent": "R2_STEP_9",
        "parent_adapter_identity": PARENT_ADAPTER,
        "parent_checkpoint_identity": PARENT_CHECKPOINT,
        "factorial": "2_TARGET_SIGNALS_X_2_RECIPE_STRENGTHS",
        "arms": arms,
        "seeds": SEEDS,
        "matched_row_order_per_seed": True,
        "fixed_training_corpus_sha256": sha(SOURCE),
        "training_rows": len(rows),
        "targeted_rows": len(targeted),
        "replay_rows": len(replay),
        "fixed_development_manifest_identity": benchmark["manifest_identity"],
        "fixed_evaluation_identity": evaluation["evaluation_identity"],
        "fixed_deterministic_decoding": evaluation["deterministic_decoding"],
        "target_signal_contrast": "UNIFORM_FINAL_TARGET_VS_CONTRACT_CRITICAL_SPAN_WEIGHTING_ON_IDENTICAL_TARGET_BYTES",
        "recipe_contrast": "LR_5E_7_VS_1E_6_WITH_ALL_OTHER_RECIPE_FIELDS_IDENTICAL",
        "claims_allowed": ["TARGET_SIGNAL_CAUSAL_EFFECT_UNDER_MATCHED_RECIPES", "RECIPE_STRENGTH_CAUSAL_EFFECT_UNDER_MATCHED_TARGET_SIGNAL", "TARGET_BY_STRENGTH_INTERACTION"],
        "claims_forbidden": ["DEVELOPMENT_PARENT_SELECTION", "NATURALISTIC_TRANSFER", "BASE_MODEL_CAPACITY_LIMIT", "PROMOTION", "RELEASE"],
        "stop_rules": [
            "STOP_ON_ANY_MATERIAL_FACTUAL_OR_EPISTEMIC_REGRESSION_VS_R2",
            "STOP_ON_REPLAY_REGRESSION_ABOVE_ZERO_MATERIAL_CASES",
            "STOP_ON_IDENTITY_CONTAMINATION_OR_SEED_MISMATCH",
            "STOP_ON_TARGET_ACQUISITION_FAILURE_IN_ALL_ARMS",
        ],
        "decision_table": {
            "TARGET_SIGNAL": "T1_BEATS_T0_AT_MATCHED_STRENGTH_WITH_SAFETY_AND_REPLAY_INTACT",
            "RECIPE_UNDERPOWERED": "S1_BEATS_S0_FOR_BOTH_SIGNALS_WITH_SAFETY_AND_REPLAY_INTACT",
            "CORPUS_GENERALIZATION": "TRAIN_ACQUISITION_PASSES_BUT_DEVELOPMENT_DOES_NOT",
            "LORA_OR_OPTIMIZATION_REVIEW": "S1_T1_CANNOT_ACQUIRE_TRAIN_CRITICAL_SPANS",
            "INTERACTION": "T1_GAIN_EXISTS_ONLY_AT_ONE_STRENGTH",
            "NO_ACTIONABLE_SIGNAL": "NO_ARM_HAS_REPLICATED_DEVELOPMENT_GAIN",
        },
        "real_runs_authorized": False,
        "model_load_authorized": False,
        "optimizer_creation_authorized": False,
        "optimizer_steps_authorized": 0,
        "development_parent_change_authorized": False,
    }, "protocol_identity")
    protocol_path = ART / f"{PREFIX}-protocol.json"
    write_json(protocol_path, protocol)

    pack = sealed({
        "schema": "editor-factual-setup-r2-causal-diagnostic-pack",
        "schema_version": 1,
        "protocol_identity": protocol["protocol_identity"],
        "artifacts": {
            "source_training": {"path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(SOURCE), "rows": len(rows)},
            "control_signal": {"path": str(control_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(control_path), "rows": len(control)},
            "challenger_signal": {"path": str(challenger_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(challenger_path), "rows": len(challenger)},
            "recipes": {"path": str(recipes_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(recipes_path)},
            "evaluation": {"path": str(evaluation_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(evaluation_path)},
        },
        "minimal_pairs": len(pair_for) // 2,
        "critical_annotated_rows": sum(bool(x["critical_spans"]) for x in challenger),
        "replay_rows_identical_between_signals": True,
        "assistant_target_bytes_identical_between_signals": True,
        "development_training_disjoint": True,
        "historical_holdouts_read": False,
        "voice_or_chief_objective": False,
    }, "pack_identity")
    write_json(ART / f"{PREFIX}-manifest.json", pack)


if __name__ == "__main__":
    main()
