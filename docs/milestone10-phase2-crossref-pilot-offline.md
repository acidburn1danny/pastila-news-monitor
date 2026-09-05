# Milestone 10 Phase 2 — Offline Crossref Pilot Implementation

This implementation is derived from Phase 1 commit
`e75dcdea4aa6dc8b89645ec9f9dcf0c1fb0d42a8` and is intentionally incapable of
opening a network connection by itself.

## Frozen boundary

`pastila_scout.crossref_pilot_offline_v1` exposes the exact approved request as
an immutable value. A future, separately authorized transport adapter may be
passed to the one-shot capture function. The module contains no default client,
DNS operation, socket creation, credential lookup, retry, redirect, pagination,
scheduler, publisher, RFC-3161, Sigstore, or OpenAlex integration.

The response body is read incrementally with a one-byte sentinel over the
2,097,152-byte ceiling. The first excess byte produces a terminal failure.
Status and headers are captured with the exact body before response-profile or
normalization validation.

Raw response status, ordered header pairs, and body bytes have distinct SHA-256
identities. Normalized output is a different canonical identity domain and
contains the raw-capture identity. Arrays are retained internally as tuples and
nested JSON objects as immutable canonical bytes; callers receive fresh
projections, so later mutation cannot change an accepted identity.

Normalization is atomic. A malformed envelope, more than ten items, missing or
invalid DOI, invalid optional field, duplicate JSON member, non-finite JSON
value, or invalid UTF-8 prevents creation of the complete normalized record set.
The raw capture remains unchanged and independently identifiable.

## Deliberate non-authority

This phase does not authorize or implement a concrete network adapter. It does
not acquire metadata and does not authorize a future request merely because a
test double can exercise the boundary. A separate pre-network adversarial audit
and explicit owner authorization are required before any Crossref request.
