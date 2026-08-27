from __future__ import annotations

import json
import random

from pastila_scout.semantic_admission_v2.gate_f_trie_projector_v1 import GateFTokenTrieProjectorOptimizedV1
from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import StagePConstraintStateV1
from pastila_scout.semantic_admission_v2.stage_p_incremental_tracker_v1 import StagePIncrementalPrefixTrackerV1
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


def _pieces(texts):
    chars=sorted(set("".join(texts)));return {index+1:char for index,char in enumerate(chars)}


def _ledger(length,entries=1):
    records=[]
    for index in range(1,entries+1):
        records.append({"entry_id":f"P{index}","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":"x"*length,
            "authority_support":None,"commitment":"y"*min(length,500),"scope_basis":"ASSERTED",
            "event_alignment":"GOVERNED_EVENT","authority_modality":"POSSIBLE","candidate_modality":"CERTAIN_OR_ACTUAL",
            "authority_timing":"FUTURE","candidate_timing":"PRESENT","independence_group":f"G{index}"})
    return json.dumps({"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":records,
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":False}},separators=(",",":"))


def test_empty_and_nonempty_string_states_remain_distinct() -> None:
    prefix='{"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":[{"entry_id":"P1","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":"'
    empty=StagePConstraintStateV1().feed(prefix);nonempty=empty.feed("x")
    projector=StagePTokenTrieProjectorV1(token_pieces=_pieces([_ledger(2)]),eos_token_id=999)
    assert projector._cache_key(empty)!=projector._cache_key(nonempty)
    assert projector._cache_key(nonempty)==projector._cache_key(nonempty.feed("xxx"))


def test_candidate_and_baseline_allowed_sets_match_exhaustively_on_seeded_ledgers() -> None:
    rng=random.Random(71201);ledgers=[_ledger(rng.randint(1,80),rng.randint(1,3)) for _ in range(30)]
    pieces=_pieces(ledgers);baseline=GateFTokenTrieProjectorOptimizedV1(token_pieces=pieces,eos_token_id=999)
    candidate=StagePTokenTrieProjectorV1(token_pieces=pieces,eos_token_id=999)
    for raw in ledgers:
        state=StagePConstraintStateV1()
        for char in raw:
            assert baseline.allowed_token_ids(state)==candidate.allowed_token_ids(state)
            state=state.feed(char)
        assert baseline.allowed_token_ids(state)==candidate.allowed_token_ids(state)==(999,)


def test_incremental_tracker_candidate_matches_full_state_on_every_prefix() -> None:
    raw=_ledger(120,2);ids=[ord(char) for char in raw];decode=lambda values:"".join(chr(item) for item in values)
    pieces={item:chr(item) for item in set(ids)};projector=StagePTokenTrieProjectorV1(token_pieces=pieces,eos_token_id=999)
    tracker=StagePIncrementalPrefixTrackerV1()
    for end in range(len(ids)+1):
        incremental=tracker.state_for(ids[:end],decode).state;full=StagePConstraintStateV1().feed(raw[:end])
        assert incremental==full
        assert projector.allowed_token_ids(incremental)==projector.allowed_token_ids(full)


def test_invalid_streams_fail_in_dfa_before_cache_can_repair() -> None:
    for raw in ('{"wrong":',_ledger(2).replace('"ASSERTED"','"BAD"',1),_ledger(2)+"x"):
        state=StagePConstraintStateV1();failed=False
        for char in raw:
            try: state=state.feed(char)
            except ValueError: failed=True;break
        assert failed
