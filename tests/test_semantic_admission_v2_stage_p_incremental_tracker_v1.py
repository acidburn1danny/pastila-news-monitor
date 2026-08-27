from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import StagePConstraintStateV1
from pastila_scout.semantic_admission_v2.stage_p_incremental_tracker_v1 import StagePIncrementalPrefixTrackerV1


def _decode(ids): return "".join(chr(item) for item in ids)


def test_incremental_extension_matches_full_replay() -> None:
    text='{"stage_id":"PROPOSITION_LEDGER","coverage_decision":"'
    ids=[ord(char) for char in text];tracker=StagePIncrementalPrefixTrackerV1()
    for end in range(len(ids)+1):
        result=tracker.state_for(ids[:end],_decode)
        assert result.state==StagePConstraintStateV1().feed(text[:end])
    assert tracker.rebuild_steps==0 and tracker.incremental_steps==len(ids)+1


def test_branch_or_decode_divergence_rebuilds_exactly() -> None:
    tracker=StagePIncrementalPrefixTrackerV1();tracker.state_for([ord("{")],_decode)
    result=tracker.state_for([ord("{"),ord('"')],lambda ids: '{"')
    assert result.state==StagePConstraintStateV1().feed('{"')
    divergent=tracker.state_for([ord("{")],_decode)
    assert divergent.path=="FULL_REBUILD" and tracker.rebuild_steps==1
