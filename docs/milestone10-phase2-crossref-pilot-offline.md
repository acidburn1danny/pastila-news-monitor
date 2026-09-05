# Milestone 10 Phase 2 — Offline Crossref Pilot Implementation

This implementation is derived from Phase 1 commit
`e75dcdea4aa6dc8b89645ec9f9dcf0c1fb0d42a8` and is intentionally incapable of
opening a network connection by itself.

## Frozen boundary

`pastila_scout.crossref_pilot_offline_v1` reconstructs the exact approved request
inside every authoritative operation, so replacing its public display binding
cannot redirect execution. The direct adapter uses Python's platform-trusted
TLS client, exact host and port, hostname verification, a 15-second socket
timeout, and no proxy, redirect, retry, pagination, credential, scheduler,
publisher, RFC-3161, Sigstore, or OpenAlex integration. It is single-use.

The response body is read incrementally with a one-byte sentinel over the
2,097,152-byte ceiling. The first excess byte produces a terminal failure.
Status and headers are captured with the exact body before response-profile or
normalization validation.

Raw response status, ordered header pairs, and body bytes have distinct SHA-256
identities. Normalized output is a different canonical identity domain and
contains the raw-capture identity. Arrays are retained internally as tuples and
nested JSON objects as immutable canonical bytes; callers receive fresh
projections, so later mutation cannot change an accepted identity.

The raw capture also contains the frozen-request identity. The closed lifecycle
entry point writes request bytes, response headers, response body, and a manifest
to a new staging directory with exclusive files and file flushes, publishes the
directory by atomic rename, and only then attempts normalization. Failed
normalization therefore cannot erase or replace the raw evidence.

Normalization is atomic. A malformed envelope, more than ten items, missing or
invalid DOI, invalid optional field, duplicate JSON member, non-finite JSON
value, or invalid UTF-8 prevents creation of the complete normalized record set.
The raw capture remains unchanged and independently identifiable.

The accepted envelope requires root and `message` objects, `status` exactly
`ok`, `message-type` exactly `work-list`, a non-empty string `message-version`,
and an `items` array containing at most ten entries. Additional envelope members
remain only in the raw response.

## Deliberate non-authority

This phase implements but does not execute the concrete network adapter. It does
not acquire metadata and does not authorize a future request merely because a
test double can exercise the boundary. A fresh pre-network adversarial audit and
explicit owner authorization are required before any Crossref request.
