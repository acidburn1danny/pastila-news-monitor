"""Fixture-capable measurement worker for the R2 causal diagnostic.

The module has no ML imports and exposes no real-training entry point. A later
successor may bind the pure measurement functions to an authorized runtime.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path


SEEDS = (161803, 271828, 314159)
ARMS = (
    "T0_CONTROL_S0_CONTROL",
    "T0_CONTROL_S1_HIGHER_PLASTICITY",
    "T1_CONTRACT_WEIGHTED_S0_CONTROL",
    "T1_CONTRACT_WEIGHTED_S1_HIGHER_PLASTICITY",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def deterministic_order(rows: int, seed: int) -> list[int]:
    if seed not in SEEDS or rows != 72:
        raise ValueError("row-order authority mismatch")
    order = list(range(rows)); random.Random(seed).shuffle(order)
    return order


def char_span_to_byte_span(content: str, start: int, end: int) -> tuple[int, int]:
    if not (0 <= start < end <= len(content)):
        raise ValueError("character span bounds")
    return len(content[:start].encode()), len(content[:end].encode())


def map_byte_span_to_tokens(content: str, byte_span: tuple[int, int], token_char_offsets: list[tuple[int, int]]) -> list[int]:
    start, end = byte_span
    if not (0 <= start < end <= len(content.encode())):
        raise ValueError("byte span bounds")
    token_bytes = [char_span_to_byte_span(content, a, b) for a, b in token_char_offsets if a != b]
    selected = [index for index, (a, b) in enumerate(token_bytes) if a >= start and b <= end and a < b]
    if not selected:
        raise ValueError("critical span maps to zero tokens")
    covered_start = token_bytes[selected[0]][0]; covered_end = token_bytes[selected[-1]][1]
    if covered_start != start or covered_end != end:
        raise ValueError("critical span cuts tokenizer token")
    if selected != list(range(selected[0], selected[-1] + 1)):
        raise ValueError("critical token mapping is discontinuous")
    return selected


def fixture_tokenizer_offsets(content: str) -> list[tuple[int, int]]:
    """One Unicode scalar per fixture token, including whitespace."""
    return [(index, index + 1) for index in range(len(content))]


def validate_and_map_annotation(assistant: str, annotation: dict[str, object]) -> list[dict[str, object]]:
    payload = json.loads(assistant); text = payload["text"]
    encoded = json.dumps(text, ensure_ascii=False, separators=(",", ":"))[1:-1]
    marker = f'"text":"{encoded}"'; marker_start = assistant.find(marker)
    if marker_start < 0:
        raise ValueError("editorial text field not addressable")
    text_start = marker_start + len('"text":"'); text_end = text_start + len(encoded)
    offsets = fixture_tokenizer_offsets(assistant); mapped = []
    for span in annotation["critical_spans"]:
        start, end = span["start"], span["end"]
        if span.get("field") != "text" or not (text_start <= start < end <= text_end):
            raise ValueError("critical span escaped editorial text")
        if assistant[start:end] != span["text"]:
            raise ValueError("critical span content mismatch")
        byte_span = char_span_to_byte_span(assistant, start, end)
        tokens = map_byte_span_to_tokens(assistant, byte_span, offsets)
        mapped.append({"byte_start": byte_span[0], "byte_end": byte_span[1], "token_start": tokens[0], "token_end_exclusive": tokens[-1] + 1})
    return mapped


def teacher_forced_diagnostics(token_nll: list[float], critical_tokens: set[int]) -> dict[str, object]:
    if not token_nll or any(not math.isfinite(x) or x < 0 for x in token_nll):
        raise ValueError("invalid token NLL")
    if not critical_tokens or min(critical_tokens) < 0 or max(critical_tokens) >= len(token_nll):
        raise ValueError("critical token inventory")
    return {
        "full_mean_nll": sum(token_nll) / len(token_nll),
        "critical_mean_nll": sum(token_nll[i] for i in critical_tokens) / len(critical_tokens),
        "critical_token_coverage": len(critical_tokens),
    }


def adapter_delta(before: dict[str, list[float]], after: dict[str, list[float]]) -> dict[str, object]:
    if before.keys() != after.keys() or not before:
        raise ValueError("adapter tensor inventory mismatch")
    result = {}; changed = 0
    for name in sorted(before):
        if len(before[name]) != len(after[name]) or not before[name]:
            raise ValueError("adapter tensor shape mismatch")
        delta = math.sqrt(sum((b - a) ** 2 for a, b in zip(before[name], after[name], strict=True)))
        base = math.sqrt(sum(a * a for a in before[name]))
        result[name] = {"l2_delta": delta, "relative_l2": delta / base if base else None}
        changed += delta > 0
    return {"tensors": result, "changed_tensor_count": changed, "tensor_count": len(result)}


def semantic_partition(rows: list[dict[str, object]]) -> dict[str, int]:
    required = {"TRAIN_ACQUISITION", "REPLAY_RETENTION", "DEVELOPMENT_EVALUATION"}
    counts = {key: 0 for key in required}
    seen = {key: 0 for key in required}
    for row in rows:
        split = row.get("split")
        if split not in required or type(row.get("pass")) is not bool:
            raise ValueError("semantic measurement schema")
        seen[split] += 1
        counts[split] += int(row["pass"])
    if not all(seen.values()):
        raise ValueError("semantic partition inventory")
    return counts


def stop_decision(evidence: dict[str, object]) -> str:
    if evidence.get("identity_drift") or evidence.get("contamination") or evidence.get("seed_mismatch"):
        return "STOP"
    if evidence.get("material_safety_regressions", 0) > 0 or evidence.get("material_replay_regressions", 0) > 0:
        return "STOP"
    if evidence.get("all_arms_train_acquisition_failed"):
        return "STOP_AND_REVIEW_LORA_OR_OPTIMIZATION"
    if evidence.get("replicated_development_gain"):
        return "CONTINUE_CAUSAL_INTERPRETATION_ONLY"
    return "NO_ACTIONABLE_SIGNAL"


def slot_inventory() -> list[dict[str, object]]:
    slots = []
    for arm in ARMS:
        for seed in SEEDS:
            slot_id = f"{arm}__seed_{seed}"
            slots.append({"slot_id": slot_id, "arm": arm, "seed": seed, "output_subdir": slot_id.lower()})
    return slots


def fixture_run(fixture: dict[str, object], output_root: Path) -> dict[str, object]:
    if output_root.is_symlink() or not output_root.is_dir() or any(output_root.iterdir()):
        raise ValueError("fixture output root must be distinct and empty")
    slots = slot_inventory()
    if fixture["slots"] != slots:
        raise ValueError("fixture slot inventory mismatch")
    if len({slot["slot_id"] for slot in slots}) != 12 or len({slot["output_subdir"] for slot in slots}) != 12:
        raise ValueError("arm seed crossover or output alias")
    orders = {str(seed): hashlib.sha256(canonical(deterministic_order(72, seed))).hexdigest() for seed in SEEDS}
    mapped = validate_and_map_annotation(fixture["assistant_content"], fixture["annotation"])
    likelihood = {
        "before": teacher_forced_diagnostics(fixture["token_nll_before"], set(fixture["critical_tokens"])),
        "after": teacher_forced_diagnostics(fixture["token_nll_after"], set(fixture["critical_tokens"])),
    }
    delta = adapter_delta(fixture["adapter_before"], fixture["adapter_after"])
    semantic = semantic_partition(fixture["semantic_rows"])
    roots = []
    for slot in slots:
        path = output_root / slot["output_subdir"]
        if path.exists(): raise ValueError("slot output collision")
        path.mkdir(); roots.append(str(path.relative_to(output_root)))
    core = {"schema":"editor-factual-setup-r2-causal-diagnostic-fixture-receipt","schema_version":1,"status":"PASS_FIXTURE_ONLY_ZERO_REAL_EXECUTION","slots":12,"arms":4,"orders":orders,"mapped_spans":mapped,"likelihood":likelihood,"adapter_delta":delta,"semantic":semantic,"output_roots":roots,"stop_rule_probe":stop_decision(fixture["stop_evidence"]),"model_loaded":False,"optimizer_created":False,"optimizer_steps":0,"training_performed":False,"inference_performed":False}
    return {**core, "receipt_identity": hashlib.sha256(canonical(core)).hexdigest()}
