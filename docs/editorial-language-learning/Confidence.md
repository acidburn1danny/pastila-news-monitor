# Confidence

## Responsibilities and contract

`derive_confidence` uses observation count, episode/story/context diversity, consistency, recency, scope stability, editor confirmation, explicit-rule authority, counter-evidence, and conflicts. `validate_confidence` recomputes score/state and rejects manual assignment.

## Dependencies, limitations, and guarantees

Equal factors give equal results. Counter-evidence/conflicts reduce confidence; confirmation increases it. Confidence never replaces evidence, provenance, or editor review.
