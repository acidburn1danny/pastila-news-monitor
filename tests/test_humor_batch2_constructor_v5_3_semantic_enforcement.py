import pytest

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature,
    SurfaceSemanticWitness, validate_semantic_plan, validate_surface_semantics,
)


def test_pilot10_role_incompatible_terminal_actor_fails_before_realization():
    plan = (
        TypedPlanNode("L1", "FACT", "RELATION_HEAD", "MAKE_RULE", "QUAL", (), ("RULE",), "P3", True),
        TypedPlanNode("L2", "RULE", "RELATION_HEAD", "RECLASSIFY", "ZONE", ("L1",), ("ZONE_STATE",), "L1", True),
        TypedPlanNode("RESULT", "ZONE_STATE", "RELATION_HEAD", "APPLY_PROCEDURE", "DEPOT", ("L2",), (), "L2", True),
    )
    specs = (
        OperandSemanticSpec("FACT", "fact", ("RELATION",), ("TRIGGER_RULE",), (), False),
        OperandSemanticSpec("QUAL", "qualification", ("CONDITION",), ("QUALIFY",), (), False),
        OperandSemanticSpec("RULE", "rule", ("RULE",), ("RECLASSIFY_PATIENT",), ("FACT",), False),
        OperandSemanticSpec("ZONE", "zone", ("LOCATION", "PATIENT"), ("RECEIVE_CRATE",), (), False),
        OperandSemanticSpec("ZONE_STATE", "zone", ("LOCATION", "PATIENT", "CATEGORY_MEMBER"),
                            ("RECEIVE_CRATE",), ("ZONE",), True),
        OperandSemanticSpec("DEPOT", "depot", ("LOCATION", "PATIENT"), ("BE_MOVED",), (), False),
    )
    signatures = (
        PredicateSemanticSignature("MAKE_RULE", ("RELATION",), ("CONDITION",), ("TRIGGER_RULE",), ("QUALIFY",)),
        PredicateSemanticSignature("RECLASSIFY", ("RULE",), ("LOCATION",), ("RECLASSIFY_PATIENT",), ("RECEIVE_CRATE",)),
        PredicateSemanticSignature("APPLY_PROCEDURE", ("PROCEDURE_APPLIER",), ("PATIENT",), ("APPLY_PROCEDURE",), ("BE_MOVED",)),
    )
    edges = (
        EdgeNecessityWitness("L1", "L2", "RULE", "ACTOR", "RULE_APPLIES_TO_RECEIVING_ZONE", True, True),
        EdgeNecessityWitness("L2", "RESULT", "ZONE_STATE", "ACTOR", "RECLASSIFICATION_GRANTS_PROCEDURAL_POWER", True, True),
    )
    with pytest.raises(ValueError, match="actor semantic role is incompatible"):
        validate_semantic_plan(typed_plan=plan, operand_specs=specs,
                               predicate_signatures=signatures, edge_witnesses=edges)


def test_reclassification_cannot_mint_privileged_affordance():
    plan = (TypedPlanNode("RESULT", "THING", "RELATION_HEAD", "ACT", "TARGET", (), (), "P", True),)
    specs = (
        OperandSemanticSpec("SOURCE", "same", ("PATIENT",), ("BE_CLASSIFIED",), (), False),
        OperandSemanticSpec("THING", "same", ("PATIENT",), ("BE_CLASSIFIED", "APPLY_PROCEDURE"), ("SOURCE",), True),
        OperandSemanticSpec("TARGET", "target", ("PATIENT",), ("BE_AFFECTED",), (), False),
    )
    signatures = (PredicateSemanticSignature("ACT", ("PATIENT",), ("PATIENT",), (), ("BE_AFFECTED",)),)
    with pytest.raises(ValueError, match="privileged affordance"):
        validate_semantic_plan(typed_plan=plan, operand_specs=specs,
                               predicate_signatures=signatures, edge_witnesses=())


def test_role_compatible_necessary_edge_and_surface_witness_pass():
    plan = (
        TypedPlanNode("L1", "RULE", "RELATION_HEAD", "CREATE", "INPUT", (), ("OUTPUT",), "P", True),
        TypedPlanNode("RESULT", "OUTPUT", "RELATION_HEAD", "AFFECT", "TARGET", ("L1",), (), "L1", True),
    )
    specs = (
        OperandSemanticSpec("RULE", "rule", ("RULE",), ("CREATE_RESULT",), (), False),
        OperandSemanticSpec("INPUT", "input", ("PATIENT",), ("BE_TRANSFORMED",), (), False),
        OperandSemanticSpec("OUTPUT", "output", ("AGENT",), ("AFFECT_TARGET",), ("INPUT",), False),
        OperandSemanticSpec("TARGET", "target", ("PATIENT",), ("BE_AFFECTED",), (), False),
    )
    signatures = (
        PredicateSemanticSignature("CREATE", ("RULE",), ("PATIENT",), ("CREATE_RESULT",), ("BE_TRANSFORMED",)),
        PredicateSemanticSignature("AFFECT", ("AGENT",), ("PATIENT",), ("AFFECT_TARGET",), ("BE_AFFECTED",)),
    )
    edges = (EdgeNecessityWitness("L1", "RESULT", "OUTPUT", "ACTOR", "EXPLICIT_RULE", True, True),)
    surface = (
        SurfaceSemanticWitness("L1", "RULE", ("RULE",), ("CREATE_RESULT",), "CREATE", "INPUT",
                               ("PATIENT",), ("BE_TRANSFORMED",), ()),
        SurfaceSemanticWitness("RESULT", "OUTPUT", ("AGENT",), ("AFFECT_TARGET",), "AFFECT", "TARGET",
                               ("PATIENT",), ("BE_AFFECTED",), ("EXPLICIT_RULE",)),
    )
    coverage = validate_surface_semantics(typed_plan=plan, operand_specs=specs,
                                          predicate_signatures=signatures, edge_witnesses=edges,
                                          surface_witnesses=surface)
    assert (coverage.nodes_validated, coverage.edges_validated, coverage.terminal_edge_validated) == (2, 1, True)
