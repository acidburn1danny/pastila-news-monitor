# Conflict Engine

## Responsibilities and contract

A conflict records controlled type, involved preferences, predecessor, successor, evidence, explanation, non-positive confidence impact, review requirement, and resolution status. Validation rejects orphan references and inconsistent resolution state.

## Dependencies, limitations, and guarantees

Resolution is deterministic and explicit rules take precedence. It never deletes evidence, hides history, silently overrides a rule, or invents a preference.
