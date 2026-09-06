# Milestone 10 Phase 5 — Bounded Crossref Production Capture

## Status

Prepared and qualified offline. Production execution has not been authorized or
performed. The public entry may be invoked only after an independent review of
the eventual committed Phase 5 authority and a separate, exact owner
authorization.

## Accepted predecessor

Milestone 10 Phase 4 is closed as `COMPLETE / PASS` by
`docs/artifacts/milestone10-closure-crossref-production-qualification-v1.json`.
Its public authority is ref
`refs/heads/milestone10/phase4-crossref-production-qualification`, commit
`54037f907f16ecb3aefe4fd7128b948d4f862d4c`, tree
`87e9ce4619223bc9ba216ce5c96aa85c3386d70f`, and qualification SHA-256
`53a465a2983ea9f32cbd8c54ac9fc12c470e3c82d4e896f1690627c03a86f10b`.

## Exact execution boundary

`execute_bounded_crossref_production_capture_v1` is the only public execution
entry. It accepts no caller-selected root, uses only the fixed
repository-relative authority root, creates that new real root, and durably writes
`attempt-consumed.json` before constructing or invoking transport. It then uses
the exact Phase 2 `DirectCrossrefHttpsTransportV1` and frozen request:

- Crossref only: `api.crossref.org:443` over HTTPS;
- GET with the exact frozen target and ordered query;
- exactly one request, one page, zero redirects, and zero retries;
- one total 15-second monotonic deadline;
- pinned CA-bundle bytes and hostname/certificate validation;
- `Accept-Encoding: identity` and a 2,097,152-byte streaming body cap;
- response status `200`, exact `application/json` Content-Type, strict UTF-8
  JSON, the Crossref work-list envelope, and at most 10 records.

The immutable raw request, wire request, parsed headers, body, and manifest are
written before profile/schema validation. The completion receipt is published
last through synchronized pending bytes and atomic no-overwrite publication.
The receipt binds the request identity, raw-capture identity, and record count.
The production receipt also declares `transport_mode=PRODUCTION_DIRECT_HTTPS`.
The injectable private test seam can emit only
`transport_mode=OFFLINE_QUALIFICATION`; its artifacts cannot claim production
transport provenance.

Before any mutation, runtime closure checks bind the complete Phase 2 request,
TLS, bounded-read, response-profile, and normalization helper graph plus the
actual `HTTPSConnection`, SSL-context, monotonic-clock, and CA-location entry
points. Rebinding any covered production dependency fails before the execution
root is created.

Any failure or interruption consumes the root permanently. There is no retry,
redraw, pagination, recovery, alternate transport, or second-request path.
Re-execution requires a new root and therefore a new, separately authorized
production request; the program never creates that authority itself.

## Deliberate exclusions

Phase 5 does not persist normalized records, integrate or mutate accepted
state, publish downstream, schedule execution, access OpenAlex, use RFC-3161 or
Sigstore, or perform any request during qualification. The normalized object is
created transiently only to validate schema and enforce the ten-record maximum.
Admission and integration of a newly captured response require a separately
defined later phase.
