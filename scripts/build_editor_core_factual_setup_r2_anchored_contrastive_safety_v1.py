from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-factual-setup-r2-anchored-contrastive-safety-v1"
SOURCE = ART / "editor-core-factual-setup-corrective-v1-training.jsonl"
T1_SIGNAL = ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl"
RECIPES = ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-recipes.json"
EVALUATION = ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-evaluation.json"
FACTORIAL_RESULT = ART / "editor-core-factual-setup-r2-causal-diagnostic-terminal-result-v1.json"
REPLAY_RESULT = ART / "editor-core-factual-setup-r2-t1s0-replay-protected-deterministic-result-v1.json"
SEEDS = [161803, 271828, 314159]
FAILURE_CLASSES = [
    "INVENTED_ACTOR",
    "ENTITY_SUBSTITUTION",
    "CATEGORICAL_ALLEGATION",
    "LOST_QUALIFICATION",
    "INCOMPLETE_NUMERIC_RECONCILIATION",
    "INCOMPLETE_PROCEDURAL_STATUS",
]
LAYER_GROUPS = ["EARLY_ATTENTION", "EARLY_MLP", "MIDDLE_ATTENTION", "MIDDLE_MLP", "LATE_ATTENTION", "LATE_MLP"]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def identified(value: dict, field: str) -> dict:
    core = dict(value)
    core.pop(field, None)
    return {**core, field: digest_bytes(canonical(core))}


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes(b"".join(canonical(row) + b"\n" for row in rows))


def mutate_text(text: str, failure_class: str) -> tuple[str, str]:
    if failure_class == "INVENTED_ACTOR":
        old, new, rule = "Direcția tehnică anunță", "Primarul și Direcția tehnică anunță", "INSERT_UNSUPPORTED_ACTOR"
        if old not in text:
            raise ValueError("invented actor mutation basis")
        return text.replace(old, new, 1), rule
    if failure_class == "ENTITY_SUBSTITUTION":
        changed, count = re.subn(r"Entitatea Entity_Substitution \d+", "Operatorul municipal", text, count=1)
        if count != 1:
            raise ValueError("entity substitution mutation basis")
        return changed, "SUBSTITUTE_BOUND_ENTITY"
    if failure_class == "CATEGORICAL_ALLEGATION":
        if "ar fi omis" not in text:
            raise ValueError("categorical mutation basis")
        return text.replace("ar fi omis", "a omis", 1), "COLLAPSE_ALLEGATION_MODALITY"
    if failure_class == "LOST_QUALIFICATION":
        changed, count = re.subn(r", numai dacă precipitațiile continuă până joi", "", text, count=1)
        if count != 1:
            raise ValueError("qualification mutation basis")
        return changed, "REMOVE_CONDITION"
    if failure_class == "INCOMPLETE_NUMERIC_RECONCILIATION":
        changed, count = re.subn(r", dintre care \d+ erau înregistrări duplicate", "", text, count=1)
        if count != 1:
            raise ValueError("numeric mutation basis")
        return changed, "OMIT_RECONCILIATION_COMPONENT"
    if failure_class == "INCOMPLETE_PROCEDURAL_STATUS":
        if "a propus suspendarea" not in text:
            raise ValueError("procedural mutation basis")
        return text.replace("a propus suspendarea", "a suspendat", 1), "COLLAPSE_PROPOSAL_TO_FINAL_ACT"
    raise ValueError("unknown failure class")


def main() -> None:
    corpus = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    signal = [json.loads(line) for line in T1_SIGNAL.read_text(encoding="utf-8").splitlines()]
    recipes = json.loads(RECIPES.read_text(encoding="utf-8"))
    evaluation = json.loads(EVALUATION.read_text(encoding="utf-8"))
    factorial_result = json.loads(FACTORIAL_RESULT.read_text(encoding="utf-8"))
    replay_result = json.loads(REPLAY_RESULT.read_text(encoding="utf-8"))
    if len(corpus) != 72 or len(signal) != 72 or len({row["example_id"] for row in corpus}) != 72:
        raise ValueError("source inventory")
    by_signal = {row["example_id"]: row for row in signal}

    pairs = []
    retention = []
    coverage = {name: 0 for name in FAILURE_CLASSES}
    for row in corpus:
        assistant = json.loads(row["messages"][-1]["content"])
        signal_row = by_signal[row["example_id"]]
        assistant_sha = digest_bytes(row["messages"][-1]["content"].encode())
        if signal_row["assistant_target_sha256"] != assistant_sha:
            raise ValueError("assistant identity")
        if row["split"] == "CORRECTIVE_TARGETED":
            rejected_text, mutation = mutate_text(assistant["text"], row["failure_class"])
            rejected = {**assistant, "text": rejected_text}
            chosen_scaffold = {key: value for key, value in assistant.items() if key != "text"}
            rejected_scaffold = {key: value for key, value in rejected.items() if key != "text"}
            if chosen_scaffold != rejected_scaffold or rejected_text == assistant["text"]:
                raise ValueError("minimal pair isolation")
            pair = {
                "schema": "editor-r2-anchored-contrastive-minimal-pair",
                "schema_version": 1,
                "pair_id": f"pair:{row['example_id']}",
                "example_id": row["example_id"],
                "failure_class": row["failure_class"],
                "minimal_pair_family": signal_row["minimal_pair_id"],
                "mutation_rule": mutation,
                "changed_field_only": "text",
                "chosen_response": row["messages"][-1]["content"],
                "chosen_sha256": assistant_sha,
                "rejected_response": json.dumps(rejected, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "request_sha256": digest_bytes(row["messages"][-2]["content"].encode()),
                "voice_or_chief_objective": False,
            }
            pair["rejected_sha256"] = digest_bytes(pair["rejected_response"].encode())
            pairs.append(pair)
            coverage[row["failure_class"]] += 1
        elif row["split"] == "REPLAY_PROTECTION":
            retention.append({
                "schema": "editor-r2-logit-retention-anchor",
                "schema_version": 1,
                "example_id": row["example_id"],
                "failure_class": row["failure_class"],
                "request_sha256": digest_bytes(row["messages"][-2]["content"].encode()),
                "assistant_target_sha256": assistant_sha,
                "anchor": "R2_STEP_9_FROZEN_LOGITS",
                "token_domain": "EDITORIAL_TEXT_VALUE_PLUS_TERMINAL_EOS",
                "kl_direction": "KL_P_R2_TO_P_CANDIDATE",
                "reference_logits_persisted": False,
                "historical_holdout": False,
            })
        else:
            raise ValueError("source split")
    if len(pairs) != 48 or len(retention) != 24 or set(coverage.values()) != {8}:
        raise ValueError("pack coverage")

    pairs_path = ART / f"{PREFIX}-minimal-pairs.jsonl"
    retention_path = ART / f"{PREFIX}-retention-anchors.jsonl"
    write_jsonl(pairs_path, pairs)
    write_jsonl(retention_path, retention)

    arms = [
        {"arm_id": "P0_POSITIVE_ONLY_K0_NO_KL", "contrastive": False, "r2_kl": False, "execution_role": "FROZEN_EXISTING_T1_S0_REFERENCE"},
        {"arm_id": "P1_CONTRASTIVE_K0_NO_KL", "contrastive": True, "r2_kl": False, "execution_role": "DISPOSABLE_RESEARCH"},
        {"arm_id": "P0_POSITIVE_ONLY_K1_R2_KL", "contrastive": False, "r2_kl": True, "execution_role": "DISPOSABLE_RESEARCH"},
        {"arm_id": "P1_CONTRASTIVE_K1_R2_KL", "contrastive": True, "r2_kl": True, "execution_role": "DISPOSABLE_RESEARCH"},
    ]
    protocol = identified({
        "schema": "editor-r2-anchored-contrastive-safety-diagnostic-protocol",
        "schema_version": 1,
        "status": "DESIGN_FIXTURE_ONLY_NO_MODEL_AUTHORITY",
        "parent": "R2_STEP_9",
        "parent_adapter_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        "weighted_sft_t1s0_line": "CLOSED_REFERENCE_ONLY",
        "factorial": "2_CONTRASTIVE_LEVELS_X_2_R2_KL_LEVELS",
        "arms": arms,
        "seeds": SEEDS,
        "fixed": {
            "source_training_sha256": digest(SOURCE),
            "t1_signal_sha256": digest(T1_SIGNAL),
            "recipe": "S0_CONTROL",
            "recipe_identity": recipes["recipes_identity"],
            "learning_rate": recipes["levels"]["S0_CONTROL"]["learning_rate"],
            "evaluator_identity": evaluation["evaluation_identity"],
            "deterministic_decoding": evaluation["deterministic_decoding"],
            "row_order_matched_per_seed": True,
        },
        "objectives": {
            "positive_sft": {"source": "T1_CONTRACT_WEIGHTED", "text_tokens_only": True, "critical_weight": "3.0"},
            "contrastive": {"form": "HINGE_ON_LENGTH_NORMALIZED_CHOSEN_MINUS_REJECTED_LOG_PROB", "margin_nats_per_token": "0.25", "weight": "1.0", "changed_field_only": "text"},
            "r2_kl": {"form": "FORWARD_KL_P_R2_TO_P_CANDIDATE", "weight": "0.10", "domain": "24_REPLAY_TEXT_VALUES_PLUS_EOS", "r2_frozen": True},
        },
        "causal_contrasts": {
            "CONTRASTIVE_EFFECT_AT_K0": ["P0_POSITIVE_ONLY_K0_NO_KL", "P1_CONTRASTIVE_K0_NO_KL"],
            "CONTRASTIVE_EFFECT_AT_K1": ["P0_POSITIVE_ONLY_K1_R2_KL", "P1_CONTRASTIVE_K1_R2_KL"],
            "KL_EFFECT_AT_P0": ["P0_POSITIVE_ONLY_K0_NO_KL", "P0_POSITIVE_ONLY_K1_R2_KL"],
            "KL_EFFECT_AT_P1": ["P1_CONTRASTIVE_K0_NO_KL", "P1_CONTRASTIVE_K1_R2_KL"],
        },
        "claims_allowed": ["CONTRASTIVE_OBJECTIVE_CAUSAL_EFFECT", "R2_KL_RETENTION_CAUSAL_EFFECT", "CONTRASTIVE_BY_KL_INTERACTION"],
        "claims_forbidden": ["PARENT_SELECTION", "NATURALISTIC_TRANSFER", "BASE_MODEL_LIMIT", "PROMOTION", "RELEASE"],
        "stop_rules": {
            "STOP": ["ANY_MATERIAL_FACTUAL_OR_EPISTEMIC_REGRESSION", "ANY_MATERIAL_REPLAY_REGRESSION", "NOVEL_ACTOR_OR_REPETITION", "NONFINITE_OR_ZERO_REQUIRED_GRADIENT"],
            "REVISE": ["CONTRASTIVE_MARGIN_IMPROVES_BUT_RETENTION_BUDGET_FAILS", "SYSTEMATIC_NEGATIVE_GRADIENT_COSINE_UNRESOLVED_BY_KL_ARM"],
            "CONTINUE_RESEARCH": ["REPLICATED_DEVELOPMENT_GAIN_AT_LEAST_2_OF_3_SEEDS", "ZERO_MATERIAL_REPLAY_REGRESSIONS", "PAIRWISE_MARGIN_POSITIVE_ALL_FAILURE_CLASSES", "RETENTION_AND_CONFLICT_GATES_PASS"],
        },
        "historical_holdouts_allowed": False,
        "model_load_authorized": False,
        "optimizer_creation_authorized": False,
        "optimizer_steps_authorized": 0,
        "training_authorized": False,
        "inference_authorized": False,
        "parent_selection_authority": False,
    }, "protocol_identity")
    protocol_path = ART / f"{PREFIX}-protocol.json"
    write_json(protocol_path, protocol)

    gradient_probe = identified({
        "schema": "editor-r2-anchored-gradient-conflict-probe",
        "schema_version": 1,
        "parent": "R2_STEP_9",
        "failure_classes": FAILURE_CLASSES,
        "layer_groups": LAYER_GROUPS,
        "measurements": ["L2_GRADIENT_NORM", "COSINE_CORRECTIVE_VS_REPLAY_CE", "PAIRWISE_MARGIN_GRADIENT_NORM", "VIRTUAL_STEP_R2_KL_CURVATURE"],
        "zero_gradient_trap_avoided": "REPLAY_CE_GRADIENT_AT_R2_FOR_CONFLICT; KL_MEASURED_AFTER_FUNCTIONAL_VIRTUAL_CORRECTIVE_DISPLACEMENT",
        "virtual_step": {"mutates_model": False, "optimizer_created": False, "scale": "S0_LEARNING_RATE", "parameter_domain": "R2_LORA_TRAINABLE_PARAMETERS_ONLY"},
        "layer_group_rule": "TRANSFORMER_DEPTH_TERCILE_X_ATTENTION_OR_MLP_LORA_PARAMETER",
        "conflict_thresholds": {"strong_negative_cosine_lte": "-0.10", "near_orthogonal_abs_lt": "0.05", "nonfinite_allowed": False, "zero_required_norm_allowed": False},
        "receipts": ["PER_FAILURE_CLASS_LAYER_GROUP", "AGGREGATE_CONFLICT_MATRIX", "VIRTUAL_STEP_KL_DRIFT"],
        "model_load_authorized": False,
        "backward_authorized": False,
        "optimizer_creation_authorized": False,
    }, "gradient_probe_identity")
    gradient_path = ART / f"{PREFIX}-gradient-probe.json"
    write_json(gradient_path, gradient_probe)

    slots = []
    for arm in arms:
        for seed in SEEDS:
            slots.append({"slot_id": f"{arm['arm_id']}__seed_{seed}", "arm_id": arm["arm_id"], "seed": seed, "output_root_policy": "DISTINCT_EMPTY", "real_execution_authorized": False})
    boundary = identified({
        "schema": "editor-r2-anchored-contrastive-safety-fixture-boundary",
        "schema_version": 1,
        "protocol_identity": protocol["protocol_identity"],
        "gradient_probe_identity": gradient_probe["gradient_probe_identity"],
        "pairs_sha256": digest(pairs_path),
        "retention_sha256": digest(retention_path),
        "arms": [arm["arm_id"] for arm in arms],
        "seeds": SEEDS,
        "slots": slots,
        "fixture_measurements": ["PAIR_ISOLATION", "CONTRASTIVE_MARGIN", "KL_NONNEGATIVITY", "GRADIENT_COSINE_BY_FAILURE_AND_LAYER", "OUTPUT_ISOLATION", "STOP_REVISE_CONTINUE"],
        "receipt_publication": "ATOMIC_TERMINAL_LAST",
        "failure_semantics": "NO_PARTIAL_ELIGIBLE_EVIDENCE",
        "historical_holdouts_allowed": False,
        "model_load_authorized": False,
        "optimizer_creation_authorized": False,
        "training_authorized": False,
        "inference_authorized": False,
        "parent_selection_authority": False,
    }, "boundary_identity")
    boundary_path = ART / f"{PREFIX}-execution-boundary.json"
    write_json(boundary_path, boundary)

    manifest = identified({
        "schema": "editor-r2-anchored-contrastive-safety-pack",
        "schema_version": 1,
        "protocol_identity": protocol["protocol_identity"],
        "gradient_probe_identity": gradient_probe["gradient_probe_identity"],
        "boundary_identity": boundary["boundary_identity"],
        "source_training_sha256": digest(SOURCE),
        "t1_signal_sha256": digest(T1_SIGNAL),
        "minimal_pairs_sha256": digest(pairs_path),
        "retention_anchors_sha256": digest(retention_path),
        "minimal_pairs": len(pairs),
        "retention_anchors": len(retention),
        "coverage": coverage,
        "factorial_arms": 4,
        "seeds": SEEDS,
        "fixture_slots": len(slots),
        "factorial_source_result_identity": factorial_result["result_identity"],
        "replay_protected_source_result_identity": replay_result["result_identity"],
        "historical_holdouts_read": False,
        "voice_or_chief_objective": False,
        "real_execution_authorized": False,
    }, "pack_identity")
    write_json(ART / f"{PREFIX}-manifest.json", manifest)


if __name__ == "__main__":
    main()
