# Milestone 10 Phase 1 — Crossref Pilot Authority Design

This phase is design-only and is bound to accepted Core V2 foundation commit
`3fa29f45ae3d4ee57b495f39dc5518776c5c2da2`.

## Authorized boundary

- Registry: Crossref only.
- Transport class: read-only HTTPS.
- Request count: one deterministic query.
- Result ceiling: ten records.
- Raw response bytes and normalized records: separate identity domains.
- OpenAlex, scheduling, downstream publishing, RFC-3161, Sigstore, network
  requests, metadata acquisition, and Phase 2 execution: prohibited.

The passive executable representation is
`pastila_scout.crossref_pilot_authority_v1`. It contains no transport client,
endpoint, credential lookup, persistence implementation, scheduler, or capture
entry point.

The byte-exact durable representation is
`docs/artifacts/milestone10-phase1-crossref-pilot-authority-design-v1.json`,
with SHA-256
`3ee1f209bf4b83c07d47b95c7bc4f76485bfcbfe7b7f73cffb5664fd533555c4`.

## Unresolved owner authority

Phase 1 does not invent either value that determines the acquired dataset:

1. the exact Crossref HTTPS endpoint;
2. the exact canonical ordered query parameters and values.

These values require explicit owner approval before a Phase 2 request authority
can exist. Query canonicalization, response limits, raw storage paths,
normalization schema, timeout, retry behavior, redirect behavior, user-agent
identity, retention, and acceptance criteria also remain undesigned and grant no
execution authority.

## Phase 2 gate

Phase 2 is not eligible. Its next design must bind the owner-approved endpoint
and query, define one-shot transport behavior, keep raw and normalized identities
separate, and prove offline that no alternate registry or request is reachable.
No network operation may occur while any required value remains unresolved.
