from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pastila_scout.semantic_admission_v2.gate_f_constraint_v1 import GateFConstraintStateV1
from pastila_scout.semantic_admission_v2.models import GateResponseV2
from pastila_scout.semantic_admission_v2.staged_gate_f_contract_v1 import (
    PropositionLedgerV1, StagedGateFPromptContractV1, canonical_stage_p_schema,
    validate_source_membership,
)

ROOT = Path(__file__).resolve().parents[1]


def _ledger(**changes):
    value = {
        "stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE",
        "entries":[{"entry_id":"P1","entry_type":"CONTAINED_CREATIVE","candidate_span":"hotelul",
            "authority_support":None,"commitment":"figură editorială conținută","scope_basis":"CREATIVE_CONTAINED",
            "event_alignment":"CREATIVE_VEHICLE_ONLY","authority_modality":"NOT_APPLICABLE",
            "candidate_modality":"NOT_APPLICABLE","authority_timing":"NOT_APPLICABLE",
            "candidate_timing":"NOT_APPLICABLE","independence_group":"G1"}],
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
            "creative_scope_checked":True,"unresolved_scope_present":False},
    }
    value.update(changes)
    return value


def _parse(value):
    return PropositionLedgerV1.model_validate_json(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def test_prompts_are_exact_unpadded_and_have_distinct_identities() -> None:
    contract = StagedGateFPromptContractV1(ROOT)
    p = contract.render_stage_p(factual_summary="Rezumat guvernat.", candidate="hotelul")
    ledger = _parse(_ledger())
    c = contract.render_stage_c(factual_summary="Rezumat guvernat.", candidate="hotelul", ledger=ledger)
    assert p == p.strip() and c == c.strip()
    assert "FSEM_CERTAINTY_MUTATION" not in p
    assert "untrusted assistive evidence" in c
    assert "{stage_p_ledger}" not in c
    assert contract.stage_p_prompt_identity != contract.stage_c_prompt_identity


def test_persisted_schema_and_runtime_model_accept_same_complete_ledger() -> None:
    value = _ledger()
    schema = json.loads((ROOT / "docs/schemas/semantic-admission-v2-stage-p-ledger-v1.schema.json").read_text("utf-8"))
    Draft202012Validator(schema).validate(value)
    _parse(value)
    assert canonical_stage_p_schema()["properties"]["entries"]["maxItems"] == 8


def test_complete_rejects_unresolved_or_false_receipt_and_never_repairs() -> None:
    value = _ledger()
    value["entries"][0]["scope_basis"] = "UNRESOLVED"
    with pytest.raises(ValueError, match="unresolved"):
        _parse(value)
    empty = _ledger(entries=[])
    with pytest.raises(ValueError):
        _parse(empty)


def test_source_membership_is_exact_and_nonsemantic() -> None:
    ledger = _parse(_ledger())
    validate_source_membership(ledger, factual_summary="Rezumat guvernat.", candidate="Acesta este hotelul.")
    with pytest.raises(ValueError, match="CANDIDATE_SPAN"):
        validate_source_membership(ledger, factual_summary="Rezumat guvernat.", candidate="Alt text.")


def test_stage_c_reuses_existing_gate_f_schema_and_character_constraint() -> None:
    raw = '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}'
    assert GateFConstraintStateV1().feed(raw).can_eos
    parsed = GateResponseV2.model_validate_json(raw)
    schema = json.loads((ROOT / "docs/schemas/semantic-admission-v2-stage-c-gate-f-v1.schema.json").read_text("utf-8"))
    Draft202012Validator(schema).validate(json.loads(raw))
    assert parsed.decision.value == "PASS"


def test_contract_has_no_executor_or_provider_import_edge() -> None:
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/staged_gate_f_contract_v1.py").read_text("utf-8")
    assert "provider_execution" not in source
    assert "def __call__" not in source
    assert "execute(" not in source
