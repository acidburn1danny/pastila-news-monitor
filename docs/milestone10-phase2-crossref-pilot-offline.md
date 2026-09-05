# Milestone 10 Phase 2 — Offline Crossref Pilot Implementation

This implementation is derived from Phase 1 commit
`e75dcdea4aa6dc8b89645ec9f9dcf0c1fb0d42a8` and is intentionally incapable of
opening a network connection by itself.

## Frozen boundary

`pastila_scout.crossref_pilot_offline_v1` reconstructs the exact approved request
inside every authoritative operation, so replacing its public display binding
cannot redirect execution. The direct adapter verifies and exclusively loads
the existing Certifi CA bundle identity
`9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f`,
ignoring environment-selected CA paths. It uses the exact host and port,
hostname verification, a monotonic 15-second deadline, and no proxy, redirect,
retry, pagination, credential, scheduler,
publisher, RFC-3161, Sigstore, or OpenAlex integration. It is single-use.

The response body is read incrementally with a one-byte sentinel over the
2,097,152-byte ceiling. The first excess byte produces a terminal failure.
Status and headers are captured with the exact body before response-profile or
normalization validation.

Response status, canonical ordered parsed-header pairs, and raw body bytes have
distinct SHA-256 identities. No claim to raw HTTP header wire bytes is made.
Normalized output is a different canonical identity domain and
contains the raw-capture identity. Arrays are retained internally as tuples and
nested JSON objects as immutable canonical bytes; callers receive fresh
projections, so later mutation cannot change an accepted identity.

The raw capture also contains an identity over the semantic profile and exact
HTTP/1.1 wire-request hash. The wire request includes the exact request line,
`Host`, approved headers, CRLF framing, and terminal empty line. The closed
lifecycle first publishes an exclusive durable `CONSUMED_BEFORE_TRANSPORT`
record shared by the execution root. It then writes semantic request bytes,
wire request bytes, parsed response headers, raw response body, and a manifest
to a new staging directory with exclusive files and file flushes, publishes the
directory by no-replacement rename, and only then attempts normalization. Failed
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
