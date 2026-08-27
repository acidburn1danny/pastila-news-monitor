from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.gate_f_constraint_v1 import (
    ConstraintViolation,
    GateFConstraintStateV1,
    GateFTokenProjectorV1,
)
from pastila_scout.semantic_admission_v2.models import GateResponseV2


PASS = '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}'
FAIL = '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din cauza","authority_support":null,"unsupported_proposition":"cauzalitate nesusținută","confidence":0.90}]}'
INDETERMINATE = '{"gate_id":"FACTUAL_SEMANTIC","decision":"INDETERMINATE","reason_records":[{"code":"ADMISSION_INDETERMINATE","status":"DECISIVE","candidate_span":null,"authority_support":null,"unsupported_proposition":"autoritate insuficientă","confidence":0.5}]}'


@pytest.mark.parametrize("raw", [PASS, FAIL, INDETERMINATE])
def test_streaming_constraint_accepts_every_canonical_response_class(raw: str) -> None:
    state = GateFConstraintStateV1()
    for char in raw:
        assert not state.can_eos
        state = state.feed(char)
    assert state.can_eos
    GateResponseV2.model_validate_json(raw, strict=True)


@pytest.mark.parametrize("chunk_size", [1, 2, 7, 31, 4096])
def test_chunking_does_not_change_constraint_result(chunk_size: int) -> None:
    state = GateFConstraintStateV1()
    for offset in range(0, len(FAIL), chunk_size):
        state = state.feed(FAIL[offset:offset + chunk_size])
    assert state.can_eos


@pytest.mark.parametrize("raw,reason", [
    ("```json\n" + PASS + "\n```", "LITERAL_MISMATCH"),
    ("answer: " + PASS, "LITERAL_MISMATCH"),
    (PASS + " ", "TRAILING_BYTES"),
    (PASS.replace("FACTUAL_SEMANTIC", "STORY_SPECIFICITY"), "LITERAL_MISMATCH"),
    (PASS.replace('"reason_records"', '"reasons"'), "LITERAL_MISMATCH"),
    (FAIL.replace("FSEM_UNSUPPORTED_CAUSALITY", "FSEM_UNKNOWN"), "ENUM_MISMATCH"),
    (FAIL.replace('"confidence":0.90', '"confidence":1.1'), "CONFIDENCE_RANGE"),
    (FAIL.replace('"confidence":0.90', '"confidence":-1'), "CONFIDENCE_RANGE"),
    (FAIL.replace('"status":"DECISIVE"', '"status":"SUPPORTING"'), "NONPASS_WITHOUT_DECISIVE_REASON"),
])
def test_constraint_rejects_noncontract_streams(raw: str, reason: str) -> None:
    with pytest.raises(ConstraintViolation, match=reason):
        GateFConstraintStateV1().feed(raw)


def test_json_string_escapes_and_multiple_records_are_supported() -> None:
    first = json.loads(FAIL)
    record = first["reason_records"][0]
    record["candidate_span"] = "linie\ncu ghilimele \"x\" și slash \\"
    record["status"] = "SUPPORTING"
    second = dict(record)
    second["status"] = "DECISIVE"
    first["reason_records"] = [record, second]
    raw = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
    assert GateFConstraintStateV1().feed(raw).can_eos


def test_record_and_character_bounds_fail_closed() -> None:
    value = json.loads(FAIL)
    value["reason_records"] = value["reason_records"] * 9
    with pytest.raises(ConstraintViolation, match="RECORD_LIMIT"):
        GateFConstraintStateV1().feed(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    prefix = FAIL.replace("din cauza", "x" * 7900)
    with pytest.raises(ConstraintViolation, match="CHARACTER_LIMIT"):
        GateFConstraintStateV1().feed(prefix)


def test_token_projection_rejects_fence_and_allows_only_eos_at_terminal() -> None:
    pieces = {0: "<eos>", 1: "{", 2: "```", 3: "x"}

    def decode(ids):
        return "".join(pieces[item] for item in ids if item != 0)

    projector = GateFTokenProjectorV1(vocabulary_ids=pieces, eos_token_id=0, decode=decode)
    assert projector.allowed_token_ids((), GateFConstraintStateV1()) == (1,)
    terminal = GateFConstraintStateV1().feed(PASS)
    assert projector.allowed_token_ids((), terminal) == (0,)


def test_token_projection_fails_closed_when_no_token_can_continue() -> None:
    projector = GateFTokenProjectorV1(vocabulary_ids=(0, 1), eos_token_id=0, decode=lambda ids: "x" * len(ids))
    with pytest.raises(ConstraintViolation, match="EMPTY_ALLOWED_TOKEN_SET"):
        projector.allowed_token_ids((), GateFConstraintStateV1())


def test_exhaustive_reference_projection_is_not_runner_eligible() -> None:
    root = Path(__file__).resolve().parents[1]
    value = json.loads((root / ".semantic-admission-v2-gate-f-constrained-decoding-v1-evidence/token-projection-preflight.json").read_text(encoding="utf-8"))
    assert value["result"] == "FAIL_PERFORMANCE"
    assert value["performance_acceptance_met"] is False
    assert value["implementation_role"] == "CORRECTNESS_ORACLE_ONLY"
    assert value["runner_integration_eligible"] is False
    assert value["model_calls"] == value["provider_calls"] == 0
