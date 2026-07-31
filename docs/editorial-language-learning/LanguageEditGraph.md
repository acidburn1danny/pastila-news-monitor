# Language Edit Graph

## Responsibilities and contract

Graphs represent transformations using semantic operations (`remove_connector`, `shorten_sentence`, `move_evidence`, `delay_payoff`, and the full controlled vocabulary), dependency edges, semantic groups, operation lineage, intent references, and fingerprint.

## Dependencies, limitations, and guarantees

Every operation intent resolves, every edge names known operations, and dependencies agree with declared order. Wording is prohibited. Meaningful order is preserved while independent references normalize deterministically.
