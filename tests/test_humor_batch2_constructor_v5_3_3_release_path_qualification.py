import unicodedata
from dataclasses import replace
import pytest

from pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path import (
    FrozenExecutableAuthorityV533,FrozenNodeRelationRule,FrozenSurfaceRoleRule,
    close_executable_authority,conditional_emit,execute_release_facing_path,
    invoke_clause_only_provider,observe_and_conform_surface,
)

def authority(forms=None):
    f=forms or {"a1":"regula cutiei","p1":"activează","b1":"condiția raftului","o1":"permisul local","a2":"permisul local","p2":"trimite","b2":"depozitul","o2":"starea finală","a3":"starea finală","p3":"închide","b3":"regula sursă"}
    nodes=(FrozenNodeRelationRule("L1","A1","P1","B1","X1",False,None),FrozenNodeRelationRule("L2","X1","P2","B2","X2",False,"L1"),FrozenNodeRelationRule("RESULT","X2","P3","B3",None,True,"L2"))
    roles=[]
    for node,prefix in zip(nodes,("1","2","3")):
        for role,key,identity in (("ACTOR","a"+prefix,node.actor_identity),("PREDICATE","p"+prefix,node.predicate_identity),("PATIENT","b"+prefix,node.patient_identity)):
            roles.append(FrozenSurfaceRoleRule(node.node_id,role,identity,f[key],(f[key],)))
        if node.produced_identity: roles.append(FrozenSurfaceRoleRule(node.node_id,"PRODUCED",node.produced_identity,f["o"+prefix],(f["o"+prefix],)))
    return FrozenExecutableAuthorityV533("AUTH","IMPL","RELEASE","SPAN","DENYSET","ALIGN",tuple(roles),nodes)

BASE="Regula cutiei activează condiția raftului și produce permisul local. Permisul local trimite depozitul și produce starea finală. Starea finală închide regula sursă."

def test_real_release_path_executes_clause_to_bytes_to_observation_to_emission():
    emitted,receipt=execute_release_facing_path(authority=authority(),provider_payload={"clause":BASE})
    assert emitted==BASE.encode("utf-8") and receipt.nodes_realized==3 and receipt.edges_realized==2 and receipt.terminal_results==1
    assert len(receipt.observed_roles)==11 and all(emitted[x.utf8_byte_start:x.utf8_byte_end]==x.surface_form.encode("utf-8") for x in receipt.observed_roles)

@pytest.mark.parametrize("extra",["node_id","actor_surface","predicate_surface","patient_surface","produced_operand_surfaces","actor_roles","affordances","causal_rule","terminal","character_start","utf8_byte_start","observed_form"])
def test_provider_injection_of_any_class_a_or_b_field_fails(extra):
    with pytest.raises(ValueError): invoke_clause_only_provider({"clause":BASE,extra:"x"})

def test_incomplete_authority_fails_before_provider_invocation():
    with pytest.raises(ValueError,match="incomplete Class A"):
        close_executable_authority(replace(authority(),release_binding_identity=""))

@pytest.mark.parametrize("bad",[
    "Condiția raftului activează regula cutiei și produce permisul local. Permisul local trimite depozitul și produce starea finală. Starea finală închide regula sursă.",
    BASE.replace("activează","mimează"),BASE.replace("condiția raftului",""),BASE.replace("permisul local","permisul străin",1),
    "Regula cutiei activează condiția raftului și produce permisul local. Depozitul trimite permisul local și produce starea finală. Starea finală închide regula sursă.",
    BASE.replace("Starea finală închide regula sursă","Starea finală admiră regula sursă"),
])
def test_semantic_role_predicate_operand_edge_and_terminal_drift_fail(bad):
    with pytest.raises(ValueError): execute_release_facing_path(authority=authority(),provider_payload={"clause":bad})

def test_ambiguous_repeated_and_missing_witnesses_fail_closed():
    with pytest.raises(ValueError):
        execute_release_facing_path(authority=authority(),provider_payload={"clause":BASE+" Regula cutiei repetată."})
    with pytest.raises(ValueError,match="missing"):
        execute_release_facing_path(authority=authority(),provider_payload={"clause":BASE.replace("regula sursă","")})

def test_licensed_romanian_case_inflection_is_coordinate_bound():
    text=BASE.replace("condiția raftului","condiției raftului")
    auth=authority(); rules=tuple(replace(x,licensed_surface_forms=("condiției raftului",)) if x.semantic_identity=="B1" else x for x in auth.role_rules)
    emitted,receipt=execute_release_facing_path(authority=replace(auth,role_rules=rules),provider_payload={"clause":text})
    witness=next(x for x in receipt.observed_roles if x.semantic_identity=="B1")
    assert witness.surface_form=="condiției raftului" and emitted[witness.utf8_byte_start:witness.utf8_byte_end]=="condiției raftului".encode()

def test_unlicensed_synonym_or_fuzzy_equivalence_fails():
    with pytest.raises(ValueError): execute_release_facing_path(authority=authority(),provider_payload={"clause":BASE.replace("depozitul","magazia")})

@pytest.mark.parametrize(("old","new","key"),[("condiția raftului","condiția unică a raftului","b1"),("activează","o activează","p1")])
def test_licensed_word_order_and_clitic_variation_remains_actual_byte_evidence(old,new,key):
    text=BASE.replace(old,new)
    forms={"a1":"regula cutiei","p1":"activează","b1":"condiția raftului","o1":"permisul local","a2":"permisul local","p2":"trimite","b2":"depozitul","o2":"starea finală","a3":"starea finală","p3":"închide","b3":"regula sursă"}; forms[key]=new
    emitted,receipt=execute_release_facing_path(authority=authority(forms),provider_payload={"clause":text})
    witnessed=next(x for x in receipt.observed_roles if x.surface_form.casefold()==new.casefold())
    assert emitted[witnessed.utf8_byte_start:witnessed.utf8_byte_end]==new.encode()

@pytest.mark.parametrize("transform",[
    lambda s:s.replace(". Permisul","; permisul"),
    lambda s:s.replace(" și produce ",", apoi produce "),
    lambda s:unicodedata.normalize("NFD",s),
])
def test_punctuation_diacritic_unicode_and_multibyte_variants_with_frozen_forms(transform):
    text=transform(BASE)
    mapping={key:transform(value) for key,value in {"a1":"regula cutiei","p1":"activează","b1":"condiția raftului","o1":"permisul local","a2":"permisul local","p2":"trimite","b2":"depozitul","o2":"starea finală","a3":"starea finală","p3":"închide","b3":"regula sursă"}.items()}
    # Whole-string transforms can affect capitalization/punctuation, so extract exact observed forms deterministically.
    for key,canonical in list(mapping.items()):
        candidates=[part for part in (transform(canonical),transform(canonical.capitalize())) if part in text]
        mapping[key]=candidates[0] if candidates else transform(canonical)
    emitted,receipt=execute_release_facing_path(authority=authority(mapping),provider_payload={"clause":text})
    assert emitted==text.encode() and all(emitted[x.utf8_byte_start:x.utf8_byte_end].decode()==x.surface_form for x in receipt.observed_roles)

def test_emitter_rejects_missing_or_mismatched_trusted_receipt():
    raw=invoke_clause_only_provider({"clause":BASE}); receipt=observe_and_conform_surface(authority=authority(),surface_bytes=raw)
    with pytest.raises(ValueError,match="trusted conformance"):
        conditional_emit(authority=authority(),surface_bytes=raw+b"!",receipt=receipt)

def test_historical_mixed_authority_runtime_is_not_reachable_from_release_module():
    import pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path as module
    source=module.__loader__.get_source(module.__name__)
    for forbidden in ("v5_3_1_runtime","AlignedSemanticNodeLexicalization","NodeLexicalization","CoordinateBoundRoleWitness","SurfaceSemanticWitness"):
        assert forbidden not in source
