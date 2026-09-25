"""Fixture-only worker. It contains no model or optimizer entry point."""
from __future__ import annotations

import hashlib
import json
import random

ARMS = ("T1_S0_EXISTING_CONTROL", "T1_S0_REPLAY_PROTECTED")
SEEDS = (161803, 271828, 314159)
TOKENIZER_SHA256 = "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def slot_id(arm: str, seed: int) -> str:
    if arm not in ARMS or seed not in SEEDS:
        raise ValueError("unauthorized arm/seed")
    return f"{arm}__seed_{seed}"


def row_order(seed: int) -> list[int]:
    if seed not in SEEDS:
        raise ValueError("unauthorized seed")
    result = list(range(72)); random.Random(seed).shuffle(result); return result


def map_spans(tokenizer, assistant: str, spans: list[dict]) -> dict:
    encoded = tokenizer(assistant, add_special_tokens=False, return_offsets_mapping=True)
    ids = list(encoded["input_ids"]); offsets = [tuple(x) for x in encoded["offset_mapping"]]
    if not ids or len(ids) != len(offsets):
        raise ValueError("tokenizer offset closure")
    mapped = []
    for span in spans:
        start, end = int(span["start"]), int(span["end"])
        if span.get("field") != "text" or start >= end or assistant[start:end] != span.get("text"):
            raise ValueError("critical span content")
        selected = [i for i, (a, b) in enumerate(offsets) if a < end and b > start and a < b]
        if not selected or selected != list(range(selected[0], selected[-1] + 1)):
            raise ValueError("critical span token continuity")
        if offsets[selected[0]][0] > start or offsets[selected[-1]][1] < end:
            raise ValueError("critical span token coverage")
        mapped.append({"char_start": start, "char_end": end, "token_start": selected[0], "token_end_exclusive": selected[-1] + 1})
    return {"token_count": len(ids), "mapped_spans": mapped, "mapping_identity": identity(mapped)}


def decide(development: dict, replay: dict) -> str:
    required = {"control", "protected"}
    if set(development) != required or set(replay) != required:
        raise ValueError("incomplete semantic evidence")
    for arm in required:
        if set(development[arm]) != set(SEEDS) or set(replay[arm]) != set(SEEDS):
            raise ValueError("incomplete seed evidence")
    if any(x["material_regressions"] for arm in replay.values() for x in arm.values()):
        return "STOP"
    protected_wins = sum(development["protected"][s]["targeted_gain"] for s in SEEDS)
    retained = sum(replay["protected"][s]["retained"] for s in SEEDS)
    if protected_wins >= 2 and retained == 3:
        return "CONTINUE_RESEARCH"
    if retained > sum(replay["control"][s]["retained"] for s in SEEDS):
        return "REVISE"
    return "STOP"


def run_fixture(tokenizer, assistant: str, spans: list[dict], output_root_id: str, arm: str, seed: int) -> dict:
    sid = slot_id(arm, seed); mapping = map_spans(tokenizer, assistant, spans)
    if output_root_id != sid:
        raise ValueError("output root is not isolated to slot")
    receipts = {
        "mapping.json": mapping,
        "teacher-forced.json": {"slot_id": sid, "before": {"full_nll": "1.5", "critical_nll": "2"}, "after": {"full_nll": "1", "critical_nll": "1.25"}, "fixture_only": True},
        "development.json": {"slot_id": sid, "deterministic": True, "targeted_gain": False, "fixture_only": True},
        "replay.json": {"slot_id": sid, "deterministic": True, "retained": True, "material_regressions": 0, "fixture_only": True},
    }
    terminal = {"slot_id": sid, "status": "PASS_FIXTURE_ONLY", "model_loaded": False, "optimizer_created": False, "optimizer_steps": 0, "training_performed": False, "inference_performed": False}
    return {"receipts": receipts, "terminal": terminal, "publication_order": [*receipts, "terminal.json"]}
