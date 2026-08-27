from __future__ import annotations

import inspect
import json

import pytest

import pastila_scout.semantic_admission_v2.stage_p_constraint_v1 as constraint_module
from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import (
    StagePConstraintStateV1,
    StagePConstraintViolationV1,
)


def _raw(*, coverage="COMPLETE", scope="CREATIVE_CONTAINED", unresolved=False):
    value = {
        "stage_id": "PROPOSITION_LEDGER",
        "coverage_decision": coverage,
        "entries": [
            {
                "entry_id": "P1",
                "entry_type": "CONTAINED_CREATIVE" if not unresolved else "UNRESOLVED_SCOPE",
                "candidate_span": "hotelul",
                "authority_support": None,
                "commitment": "figură conținută",
                "scope_basis": scope,
                "event_alignment": "CREATIVE_VEHICLE_ONLY" if not unresolved else "UNRESOLVED",
                "authority_modality": "NOT_APPLICABLE",
                "candidate_modality": "NOT_APPLICABLE",
                "authority_timing": "NOT_APPLICABLE",
                "candidate_timing": "NOT_APPLICABLE",
                "independence_group": "G1",
            }
        ],
        "coverage_receipt": {
            "candidate_reviewed_as_whole": True,
            "embedded_propositions_checked": True,
            "creative_scope_checked": True,
            "unresolved_scope_present": unresolved,
        },
    }
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def test_complete_canonical_ledger_reaches_eos() -> None:
    assert StagePConstraintStateV1().feed(_raw()).can_eos


def test_indeterminate_unresolved_ledger_is_allowed() -> None:
    raw = _raw(coverage="INDETERMINATE", scope="UNRESOLVED", unresolved=True)
    assert StagePConstraintStateV1().feed(raw).can_eos


def test_complete_with_unresolved_scope_fails_at_terminal() -> None:
    with pytest.raises(StagePConstraintViolationV1, match="INVALID_COMPLETE"):
        StagePConstraintStateV1().feed(_raw(scope="UNRESOLVED", unresolved=True))


def test_wrong_field_order_and_ninth_entry_are_constrained_out() -> None:
    with pytest.raises(StagePConstraintViolationV1):
        StagePConstraintStateV1().feed('{"coverage_decision"')
    one = json.loads(_raw())["entries"][0]
    value = json.loads(_raw())
    value["entries"] = [dict(one, entry_id=f"P{min(index, 8)}") for index in range(1, 10)]
    with pytest.raises(StagePConstraintViolationV1, match="ENTRY_LIMIT"):
        StagePConstraintStateV1().feed(
            json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        )


def test_constraint_module_has_no_provider_or_executor_edge() -> None:
    source = inspect.getsource(constraint_module).lower()
    assert "provider" not in source
    assert "executor" not in source
