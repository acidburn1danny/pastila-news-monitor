# Observation

## Responsibilities and contract

An observation is the smallest permanent unit and references exactly one validated correction provenance record, graph, intent, episode, story, editor, scope, one or more dimensions, affected policies, and a semantic fingerprint. An optional timestamp is provenance only and excluded from rendering/identity.

## Dependencies, limitations, and guarantees

Graph and intent references must resolve. Observations store no wording, never activate guidance directly, remain frozen and append-only, and preserve historical fingerprints indefinitely.
