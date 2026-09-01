# Pilot 13 extensive audit — iteration 02 finding

Verdict: `STRUCTURAL_PREDECESSOR_AND_PLANNER_RULE_SELECTION_COULD_MASQUERADE_AS_NECESSITY`

The first full post-remediation audit found that an external registry alone did not prove
necessity. A successor could name a predecessor without consuming its result, and a
planner could select one of multiple type-compatible rules with freely substitutable
consequences. Both paths could preserve topology while leaving causality arbitrary.

Remediation: every successor must consume the immediate predecessor's derived operand;
the validator independently derives the removal counterfactual. Rule resolution must be
unique for the predicate and typed arguments, including the terminal relation. Ambiguous
compatible consequences fail closed as substitutable.
