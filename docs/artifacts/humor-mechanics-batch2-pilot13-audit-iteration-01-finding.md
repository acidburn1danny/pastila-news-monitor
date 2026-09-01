# Pilot 13 extensive audit — iteration 01 finding

Verdict: `SYSTEMATIC_SELF_VALIDATING_SEMANTIC_LICENSE_AND_MISSING_ANCHOR_EDGE`

Earliest causal boundary: V5.3/V5.3.3 static semantic-plan construction and validation.

The compatibility planner authored operand roles and affordances, predicate signatures,
causal-rule labels, and true necessity booleans. The validator then tested only internal
agreement among those planner-authored claims. It had no independent semantic-rule
registry. Its edge coverage also began at typed predecessor links, omitting the selected
fact to first invented relation that G02C identified as the earliest failure.

Pilot 13 was therefore not irreducible generation randomness. Its material surface
faithfully expressed a statically accepted but semantically unlicensed plan.

Remediation: introduce a successor independent licensing boundary. Every relation,
including the anchor and terminal relation, must request a rule from a registry outside
the planner payload. Entity classes, roles, affordances, and produced semantics are
checked or derived from that trusted rule; planner ontology extension is rejected.
