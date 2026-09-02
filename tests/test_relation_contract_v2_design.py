from pastila_scout.relation_contract_v2_design import RELATIONS, P13_NEGATIVE_CODES, detect_universal_rejection, validate_design_witness

def positive(kind):
    evidence, continuity = RELATIONS[kind]
    return {"relation_class":kind,"evidence":{"relation_class":kind,"kind":evidence,"identity":"e","provenance_identity":"p","owner":"INDEPENDENT_AUTHORITY","depends_on_candidate":False},"continuity":{"kind":continuity},"operands_typed":True,"roles_compatible":True,"claimed_result_licensed":True,"alternative_results_allowed":True,"arbitrary_substitution_rejected":True,"terminal":{"authority":True,"continuity":True,"licensed_result":True,"non_arbitrary":True}}

def test_every_relation_class_has_satisfiable_positive_witness():
    assert len(RELATIONS) == 17
    assert all(not validate_design_witness(positive(k)) for k in RELATIONS)

def test_evidence_free_pass_is_impossible():
    for kind in RELATIONS:
        w=positive(kind); w["evidence"]={}
        assert validate_design_witness(w)

def test_unconditional_universal_rejection_is_detected():
    assert detect_universal_rejection({k:("HARDCODED_FAILURE",) for k in RELATIONS})
    assert not detect_universal_rejection({k:validate_design_witness(positive(k)) for k in RELATIONS})

def test_relation_class_switching_cannot_bypass_evidence_or_continuity():
    kinds=list(RELATIONS)
    for i,kind in enumerate(kinds):
        w=positive(kind); w["relation_class"]=kinds[(i+1)%len(kinds)]
        assert validate_design_witness(w)

def test_legitimate_alternatives_allowed_but_arbitrary_result_rejected():
    w=positive("PHYSICAL_ACTION"); assert not validate_design_witness(w)
    w["arbitrary_substitution_rejected"]=False
    assert "ARBITRARY_SUBSTITUTION_NOT_REJECTED" in validate_design_witness(w)

def test_terminal_gets_equal_strength_validation():
    w=positive("TEMPORAL"); w["terminal"]["authority"]=False
    assert "TERMINAL_LICENSE_MISSING" in validate_design_witness(w)

def test_p13_negative_classes_remain_explicitly_blocked():
    assert len(P13_NEGATIVE_CODES)==7 and all(P13_NEGATIVE_CODES.values())

def test_planner_or_author_cannot_own_evidence():
    for owner in ("PLANNER","RULE_AUTHOR"):
        w=positive("LOGICAL_INFERENCE"); w["evidence"]["owner"]=owner
        assert "TRUST_DOMAIN_SELF_AUTHORIZATION" in validate_design_witness(w)
