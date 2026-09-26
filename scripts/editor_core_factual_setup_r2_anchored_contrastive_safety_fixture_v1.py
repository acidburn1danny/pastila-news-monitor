"""Pure-Python fixture implementation; no model or optimizer entry point."""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict


ARMS = (
    "P0_POSITIVE_ONLY_K0_NO_KL",
    "P1_CONTRASTIVE_K0_NO_KL",
    "P0_POSITIVE_ONLY_K1_R2_KL",
    "P1_CONTRASTIVE_K1_R2_KL",
)
SEEDS = (161803, 271828, 314159)
FAILURE_CLASSES = (
    "INVENTED_ACTOR", "ENTITY_SUBSTITUTION", "CATEGORICAL_ALLEGATION",
    "LOST_QUALIFICATION", "INCOMPLETE_NUMERIC_RECONCILIATION", "INCOMPLETE_PROCEDURAL_STATUS",
)
LAYER_GROUPS = ("EARLY_ATTENTION", "EARLY_MLP", "MIDDLE_ATTENTION", "MIDDLE_MLP", "LATE_ATTENTION", "LATE_MLP")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def slot_id(arm: str, seed: int) -> str:
    if arm not in ARMS or seed not in SEEDS:
        raise ValueError("unauthorized arm/seed")
    return f"{arm}__seed_{seed}"


def contrastive_hinge(chosen_mean_logp: float, rejected_mean_logp: float, margin: float = 0.25) -> float:
    values = (chosen_mean_logp, rejected_mean_logp, margin)
    if not all(math.isfinite(value) for value in values) or margin <= 0:
        raise ValueError("contrastive inputs")
    return max(0.0, margin - (chosen_mean_logp - rejected_mean_logp))


def forward_kl(reference: list[float], candidate: list[float]) -> float:
    if len(reference) != len(candidate) or not reference:
        raise ValueError("KL shape")
    if any(value <= 0 or not math.isfinite(value) for value in reference + candidate):
        raise ValueError("KL probabilities")
    if abs(sum(reference) - 1.0) > 1e-9 or abs(sum(candidate) - 1.0) > 1e-9:
        raise ValueError("KL normalization")
    result = sum(p * math.log(p / q) for p, q in zip(reference, candidate))
    if result < -1e-12:
        raise ValueError("negative KL")
    return max(0.0, result)


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("gradient shape")
    if not all(math.isfinite(value) for value in left + right):
        raise ValueError("nonfinite gradient")
    nl = math.sqrt(sum(value * value for value in left)); nr = math.sqrt(sum(value * value for value in right))
    if nl == 0 or nr == 0:
        raise ValueError("zero required gradient")
    return sum(a * b for a, b in zip(left, right)) / (nl * nr)


def gradient_probe(corrective: dict, replay: dict) -> dict:
    expected = {(failure, layer) for failure in FAILURE_CLASSES for layer in LAYER_GROUPS}
    if set(corrective) != expected or set(replay) != expected:
        raise ValueError("gradient matrix inventory")
    rows = []
    for key in sorted(expected):
        value = cosine(corrective[key], replay[key])
        rows.append({"failure_class": key[0], "layer_group": key[1], "cosine": value, "strong_conflict": value <= -0.10})
    return {"rows": rows, "strong_conflicts": sum(row["strong_conflict"] for row in rows), "probe_identity": identity(rows)}


def validate_pair(pair: dict) -> None:
    chosen = json.loads(pair["chosen_response"]); rejected = json.loads(pair["rejected_response"])
    if pair["changed_field_only"] != "text" or chosen["text"] == rejected["text"]:
        raise ValueError("pair change")
    if {key: value for key, value in chosen.items() if key != "text"} != {key: value for key, value in rejected.items() if key != "text"}:
        raise ValueError("pair scaffold")
    if hashlib.sha256(pair["chosen_response"].encode()).hexdigest() != pair["chosen_sha256"]:
        raise ValueError("chosen identity")
    if hashlib.sha256(pair["rejected_response"].encode()).hexdigest() != pair["rejected_sha256"]:
        raise ValueError("rejected identity")


def decide(evidence: dict) -> str:
    required = {"material_regressions", "novel_actor_or_repetition", "replicated_gain_seeds", "pairwise_margin_classes", "retention_pass_seeds", "strong_unresolved_conflicts"}
    if set(evidence) != required:
        raise ValueError("decision evidence")
    if evidence["material_regressions"] or evidence["novel_actor_or_repetition"]:
        return "STOP"
    if evidence["pairwise_margin_classes"] < 6 or evidence["retention_pass_seeds"] < 3:
        return "REVISE"
    if evidence["strong_unresolved_conflicts"]:
        return "REVISE"
    return "CONTINUE_RESEARCH" if evidence["replicated_gain_seeds"] >= 2 else "STOP"


def run_fixture(arm: str, seed: int, output_root_id: str, pairs: list[dict]) -> dict:
    sid = slot_id(arm, seed)
    if output_root_id != sid:
        raise ValueError("output isolation")
    if len(pairs) != 48:
        raise ValueError("pair inventory")
    coverage = defaultdict(int)
    for pair in pairs:
        validate_pair(pair); coverage[pair["failure_class"]] += 1
    if set(coverage) != set(FAILURE_CLASSES) or set(coverage.values()) != {8}:
        raise ValueError("pair coverage")
    margin = contrastive_hinge(-0.5, -1.0)
    kl = forward_kl([0.7, 0.3], [0.6, 0.4])
    receipts = {
        "pair-validation.json": {"pairs": 48, "coverage": dict(coverage), "fixture_only": True},
        "objective.json": {"slot_id": sid, "contrastive_hinge": margin, "r2_forward_kl": kl, "fixture_only": True},
        "gradient-probe.json": {"slot_id": sid, "fixture_only": True, "failure_classes": 6, "layer_groups": 6},
    }
    terminal = {"slot_id": sid, "status": "PASS_FIXTURE_ONLY", "model_loaded": False, "optimizer_created": False, "optimizer_steps": 0, "training_performed": False, "inference_performed": False}
    return {"receipts": receipts, "terminal": terminal, "publication_order": [*receipts, "terminal.json"]}
