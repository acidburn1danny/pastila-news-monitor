from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.gate_f_trie_projector_v1 import GateFTokenTrieProjectorOptimizedV1
from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import StagePConstraintStateV1, StagePConstraintViolationV1
from pastila_scout.semantic_admission_v2.staged_gate_f_contract_v1 import PropositionLedgerV1


def _raw(*, coverage="COMPLETE", scope="CREATIVE_CONTAINED", unresolved=False):
    value={"stage_id":"PROPOSITION_LEDGER","coverage_decision":coverage,"entries":[{
        "entry_id":"P1","entry_type":"CONTAINED_CREATIVE" if not unresolved else "UNRESOLVED_SCOPE",
        "candidate_span":"hotelul","authority_support":None,"commitment":"figură conținută",
        "scope_basis":scope,"event_alignment":"CREATIVE_VEHICLE_ONLY" if not unresolved else "UNRESOLVED",
        "authority_modality":"NOT_APPLICABLE","candidate_modality":"NOT_APPLICABLE",
        "authority_timing":"NOT_APPLICABLE","candidate_timing":"NOT_APPLICABLE","independence_group":"G1"}],
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":unresolved}}
    return json.dumps(value,ensure_ascii=False,separators=(",",":"))


def test_complete_canonical_ledger_reaches_eos_and_strict_model() -> None:
    raw=_raw()
    assert StagePConstraintStateV1().feed(raw).can_eos
    PropositionLedgerV1.model_validate_json(raw)


def test_indeterminate_unresolved_ledger_is_allowed() -> None:
    raw=_raw(coverage="INDETERMINATE",scope="UNRESOLVED",unresolved=True)
    assert StagePConstraintStateV1().feed(raw).can_eos


def test_complete_with_unresolved_scope_fails_at_terminal() -> None:
    with pytest.raises(StagePConstraintViolationV1,match="INVALID_COMPLETE"):
        StagePConstraintStateV1().feed(_raw(scope="UNRESOLVED",unresolved=True))


def test_wrong_field_order_and_ninth_entry_are_constrained_out() -> None:
    with pytest.raises(StagePConstraintViolationV1):
        StagePConstraintStateV1().feed('{"coverage_decision"')
    one=json.loads(_raw())["entries"][0]
    value=json.loads(_raw()); value["entries"]=[dict(one,entry_id=f"P{min(i,8)}") for i in range(1,10)]
    with pytest.raises(StagePConstraintViolationV1,match="ENTRY_LIMIT"):
        StagePConstraintStateV1().feed(json.dumps(value,ensure_ascii=False,separators=(",",":")))


def test_optimized_token_trie_projects_without_model_or_tokenizer() -> None:
    pieces={i+1:char for i,char in enumerate(sorted(set(_raw())))}
    projector=GateFTokenTrieProjectorOptimizedV1(token_pieces=pieces,eos_token_id=999)
    state=StagePConstraintStateV1()
    allowed=projector.allowed_token_ids(state)
    opening=next(token for token,piece in pieces.items() if piece=="{")
    assert opening in allowed
    final=state.feed(_raw())
    assert projector.allowed_token_ids(final)==(999,)
    assert projector.trie_node_count > 1


def test_constraint_module_has_no_provider_or_executor_edge() -> None:
    import inspect
    import pastila_scout.semantic_admission_v2.stage_p_constraint_v1 as module
    source=inspect.getsource(module)
    assert "provider" not in source.lower()
    assert "executor" not in source.lower()
