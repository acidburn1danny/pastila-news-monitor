# Preference Decay

## Responsibilities and contract

`derive_decay` maps recency periods, counter-evidence ratio, consistency, confirmation, and deprecation reason to an activity state plus confidence adjustment, influence, and recommendation priority.

## Dependencies, limitations, and guarantees

Decay creates a new immutable artifact and never changes observations, evidence, or lineage. Explicit editor rules retain stable state, full influence, and zero automatic confidence penalty; only editor action may deprecate them.
