import json

from pastila_scout.semantic_admission_v2.stage_p_callback_controller_v1 import StagePCallbackControllerV1
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


def _raw():
    return json.dumps({"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":[{
        "entry_id":"P1","entry_type":"CONTAINED_CREATIVE","candidate_span":"hotelul","authority_support":None,
        "commitment":"figură","scope_basis":"CREATIVE_CONTAINED","event_alignment":"CREATIVE_VEHICLE_ONLY",
        "authority_modality":"NOT_APPLICABLE","candidate_modality":"NOT_APPLICABLE","authority_timing":"NOT_APPLICABLE",
        "candidate_timing":"NOT_APPLICABLE","independence_group":"G1"}],"coverage_receipt":{
        "candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,"creative_scope_checked":True,
        "unresolved_scope_present":False}},ensure_ascii=False,separators=(",",":"))


def test_controller_combines_incremental_tracking_candidate_cache_and_terminal_eos() -> None:
    raw=_raw();ids=[ord(char) for char in raw];pieces={item:chr(item) for item in set(ids)}
    controller=StagePCallbackControllerV1(projector=StagePTokenTrieProjectorV1(token_pieces=pieces,eos_token_id=999))
    decode=lambda values:"".join(chr(item) for item in values)
    final=None
    for end in range(len(ids)+1): final=controller.allowed(ids[:end],decode)
    assert final.allowed_token_ids==(999,) and final.tracking_path=="INCREMENTAL"
    assert final.tracker_rebuilds==0 and final.tracker_incremental_steps==len(ids)+1


def test_controller_receipt_exposes_progress_without_mutating_output() -> None:
    raw=_raw();ids=[ord(char) for char in raw];pieces={item:chr(item) for item in set(ids)}
    controller=StagePCallbackControllerV1(projector=StagePTokenTrieProjectorV1(token_pieces=pieces,eos_token_id=999))
    receipt=controller.allowed(ids[:20],lambda values:"".join(chr(item) for item in values))
    assert receipt.decoded_characters==20 and receipt.suffix_characters==20
    assert receipt.dfa_mode and receipt.trie_cache_size>0
