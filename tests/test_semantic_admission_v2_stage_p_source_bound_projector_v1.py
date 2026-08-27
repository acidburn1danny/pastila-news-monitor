import itertools

from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import StagePConstraintStateV1
from pastila_scout.semantic_admission_v2.stage_p_source_bound_projector_v1 import StagePSourceBoundTokenProjectorV1


CANDIDATE_PREFIX='{"stage_id":"PROPOSITION_LEDGER","coverage_decision":"INDETERMINATE","entries":[{"entry_id":"P1","entry_type":"CONTAINED_CREATIVE","candidate_span":"'


def _projector(pieces):
    return StagePSourceBoundTokenProjectorV1(token_pieces={index+1:value for index,value in enumerate(pieces)},eos_token_id=999)


def _allowed(pieces,prefix,candidate="hotelul transparent",summary="complex turistic"):
    receipt=_projector(pieces).allowed_token_ids(state=StagePConstraintStateV1().feed(prefix),decoded_prefix=prefix,
        candidate=candidate,factual_summary=summary)
    return {pieces[item-1] for item in receipt.allowed_token_ids},receipt


def test_case01_factual_summary_span_is_blocked_and_commentary_span_passes() -> None:
    bad="Un complex turistic a plătit la negru."
    good="hotelul transparent"
    allowed,receipt=_allowed([bad+'"',good+'"',"h","U"],CANDIDATE_PREFIX,candidate=good,summary=bad)
    assert good+'"' in allowed and "h" in allowed
    assert bad+'"' not in allowed and "U" not in allowed
    assert receipt.field=="candidate_span" and receipt.source_bound_count<receipt.grammar_allowed_count


def test_all_exact_substrings_and_overlaps_remain_available() -> None:
    candidate="banana"
    for value in ("b","ban","ana","nan","banana"):
        allowed,_=_allowed([value+'"',"z"],CANDIDATE_PREFIX,candidate=candidate)
        assert value+'"' in allowed and "z" not in allowed


def test_authority_support_uses_summary_and_null_remains_grammar_available() -> None:
    candidate="hotelul";summary="complex turistic"
    before=CANDIDATE_PREFIX+'hotelul","authority_support":'
    allowed,receipt=_allowed(["n",'"',"c"],before,candidate=candidate,summary=summary)
    assert receipt.field is None and "n" in allowed
    inside=before+'"'
    allowed,receipt=_allowed(['complex turistic"','hotelul"',"c","h"],inside,candidate=candidate,summary=summary)
    assert 'complex turistic"' in allowed and 'hotelul"' not in allowed
    assert receipt.field=="authority_support"


def test_romanian_unicode_direct_and_json_escape_are_exact() -> None:
    candidate='țară "clară"'
    allowed,_=_allowed(['țară"','tara"'],CANDIDATE_PREFIX,candidate=candidate)
    assert 'țară"' in allowed and 'tara"' not in allowed
    escaped=CANDIDATE_PREFIX+r'\u021b'
    state=StagePConstraintStateV1().feed(escaped)
    receipt=_projector(['ară"','ara"']).allowed_token_ids(state=state,decoded_prefix=escaped,candidate=candidate,factual_summary="x")
    allowed={['ară"','ara"'][item-1] for item in receipt.allowed_token_ids}
    assert 'ară"' in allowed and 'ara"' not in allowed


def test_non_source_fields_are_unchanged_from_grammar_projection() -> None:
    prefix=CANDIDATE_PREFIX+'hotelul","authority_support":null,"commitment":"'
    pieces=["orice text",'"',"x"]
    receipt=_projector(pieces).allowed_token_ids(state=StagePConstraintStateV1().feed(prefix),decoded_prefix=prefix,
        candidate="hotelul",factual_summary="complex")
    assert receipt.field is None and receipt.allowed_token_ids==tuple(sorted(receipt.allowed_token_ids))
    assert receipt.source_bound_count==receipt.grammar_allowed_count


def test_exhaustive_small_sources_match_exact_substring_reference() -> None:
    alphabet="ab"
    for length in range(1,4):
        for source_tuple in itertools.product(alphabet,repeat=length):
            source="".join(source_tuple)
            substrings={source[start:end] for start in range(len(source)) for end in range(start+1,len(source)+1)}
            for existing in {"",*substrings}:
                prefix=CANDIDATE_PREFIX+existing
                pieces=["a","b",'"']
                try: allowed,_=_allowed(pieces,prefix,candidate=source)
                except ValueError: allowed=set()
                for piece in pieces:
                    expected=((existing+piece) in source if piece!='"' else bool(existing) and existing in source)
                    assert (piece in allowed)==expected,(source,existing,piece)


def test_token_crossing_into_and_out_of_source_field_cannot_bypass_binding() -> None:
    before=CANDIDATE_PREFIX.removesuffix(',"candidate_span":"')
    valid=',"candidate_span":"hotelul"'
    invalid=',"candidate_span":"complex turistic"'
    allowed,receipt=_allowed([valid,invalid],before,candidate="hotelul",summary="complex turistic")
    assert valid in allowed and invalid not in allowed
    assert receipt.field is None and receipt.source_bound_count==1
