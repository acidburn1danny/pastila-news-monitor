from dataclasses import fields
import pytest
from pastila_scout.humor_batch2_development_constructor_v5_3_3_integration import CLASS_C_FIELDS,ProviderCreativeRealizationV533,parse_provider_creative_payload,observe_surface_bytes

GOOD={"clause":"a p b"}

def test_provider_schema_has_one_generative_source_of_truth():
    assert {x.name for x in fields(ProviderCreativeRealizationV533)}==CLASS_C_FIELDS=={"clause"}
    assert parse_provider_creative_payload(GOOD).clause=="a p b"

@pytest.mark.parametrize("extra",["node_id","actor_roles","actor_affordances","predecessor_causal_rule_ids","terminal_result","character_start","utf8_byte_start","alignment_rule","canonical_form","release_identity","actor_surface","predicate_surface","patient_surface","produced_operand_surfaces"])
def test_every_class_a_or_b_override_is_structurally_rejected(extra):
    with pytest.raises(ValueError,match="single Class C"):
        parse_provider_creative_payload({**GOOD,extra:"smuggled"})

def test_any_second_field_and_missing_clause_fail_closed():
    with pytest.raises(ValueError): parse_provider_creative_payload({**GOOD,"second":"x"})
    with pytest.raises(ValueError): parse_provider_creative_payload({k:v for k,v in GOOD.items() if k!="clause"})

def test_class_b_is_observed_from_actual_character_and_utf8_coordinates():
    raw="cutie eligibilă".encode("utf-8")
    evidence=observe_surface_bytes(surface_bytes=raw,character_spans=((0,15),),utf8_byte_spans=((0,len(raw)),),observed_roles=("ACTOR",))
    assert evidence.observed_forms==("cutie eligibilă",)
    with pytest.raises(ValueError,match="disagree"):
        observe_surface_bytes(surface_bytes=raw,character_spans=((0,5),),utf8_byte_spans=((1,6),),observed_roles=("ACTOR",))

def test_legacy_mixed_authority_types_are_not_imported_or_exposed():
    import pastila_scout.humor_batch2_development_constructor_v5_3_3_integration as module
    source=module.__loader__.get_source(module.__name__)
    for forbidden in ("AlignedSemanticNodeLexicalization","NodeLexicalization","SurfaceSemanticWitness","CoordinateBoundRoleWitness"):
        assert forbidden not in source and not hasattr(module,forbidden)
