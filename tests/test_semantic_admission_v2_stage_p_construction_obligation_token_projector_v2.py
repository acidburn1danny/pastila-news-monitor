from __future__ import annotations
from dataclasses import replace
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_token_projector_v1 import StagePConstructionObligationTokenProjectorV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_token_projector_v2 import StagePConstructionObligationTokenProjectorV2
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context,_valid_text

def _pair(pieces):
    context,_,_=_case_context();kwargs=dict(token_pieces=pieces,eos_token_id=99,tokenizer_identity="tok",decoder_identity="dec",excluded_token_ids=())
    return (StagePConstructionObligationTokenProjectorV1(controller=StagePConstructionObligationCharacterControllerV1(context=context,decoder_identity="dec"),**kwargs),
            StagePConstructionObligationTokenProjectorV2(controller=StagePConstructionObligationCharacterControllerV1(context=context,decoder_identity="dec"),**kwargs))

def test_split_candidate_exact_for_empty_nonempty_escape_and_boundary_states():
    context,_,_=_case_context();raw=_valid_text(context);marker='"role_basis":"';start=raw.index(marker)+len(marker)
    pieces={0:"abc",1:'abc"',2:"\\n",3:"\n",4:"ă",5:'"',6:"x\\u0041",7:"{"}
    left,right=_pair(pieces)
    for prefix in (raw[:start],raw[:start]+"x",raw[:start]+"x\\",raw[:start]+"x\\u0"):
        ids=list(range(len(prefix)));decode=lambda items,p=prefix:p[:len(items)]
        assert left.allowed_token_ids(ids,decode)==right.allowed_token_ids(ids,decode)

def test_ordinary_fast_path_respects_global_character_limit():
    left,right=_pair({0:"a",1:"ab",2:'a"'})
    context,_,_=_case_context();state=left.controller.tracker._last_state
    state=replace(state,mode="STRING",remaining="",string_characters=1,characters=15999)
    assert left._project_state(state)==right._project_state(state)==(0,)
