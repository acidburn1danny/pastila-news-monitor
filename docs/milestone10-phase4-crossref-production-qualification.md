# Milestone 10 Phase 4 — Crossref Production Capture Qualification

Phase 4 qualifies the complete production orchestration path offline. It is
based on the accepted Phase 3 authority at commit
`809be94457dcc0cc3dc6ab9f8671338882b4afb7`, tree
`4a2886f9d183bd1cdf0248e9f64e750d35478ce1`.

## Qualified boundary

`pastila_scout.crossref_production_qualification_v1` reproduces only the frozen,
transport-neutral Phase 2 request/snapshot/normalization semantics locally,
then composes them with the Phase 3 immutable integration boundary and a durable
publication/recovery boundary. It does not import the network-capable Phase 2
module. The attempt is consumed before the response snapshot is read. Raw bytes
are committed before normalization, normalized bytes before integration,
accepted state atomically, and the completion record last. Every phase-complete
marker (raw manifest, normalized record set, accepted/quarantine state, and
completion record) uses synchronized pending bytes plus atomic no-overwrite
publication.

The Phase 4 entry accepts only `OfflineCrossrefResponseV1`. Its constructor
requires the exact status, ordered parsed-header bytes, response-body bytes,
request identity, and raw-capture identity already committed by the Phase 2
proof. Phase 4 does not construct, accept, export, import, or bind a network
transport, and its fresh import closure contains no HTTP, TLS, or socket module.

Recovery never invokes transport. It reopens only regular files through a
single file descriptor, rejects symlinks and detected replacement or mutation,
revalidates the raw request, wire request, response headers/body, manifest,
normalized bytes, accepted state, Phase 3 replay, and completion closure. A
matching interrupted publication can be completed; a foreign pending artifact
fails closed. Recovery after accepted-state publication reconstructs and
publishes the original `ACCEPTED` outcome rather than reclassifying it as a new
replay outcome. Quarantine uses the same synchronized pending, atomic
no-overwrite publication, and exact pending reconciliation as accepted state.

## Preserved authority

- Crossref is the only provider represented.
- The frozen request remains one GET, ten records maximum, zero redirect,
  zero retry, one page, and a 15-second production transport deadline.
- Raw response, normalized records, integration batch, accepted state, and
  completion remain separate identity domains.
- The accepted Phase 3 integration continues to admit only the exact qualified
  Phase 2 normalized artifact; Phase 4 introduces no broader metadata
  acceptance policy.
- No retention, timing, scheduling, credential, proxy, OpenAlex, downstream
  publishing, RFC-3161, or Sigstore policy is introduced.

## Deliberate non-authority

Phase 4 performs no Crossref request and captures no new metadata. It exposes
no production network entry point. It does not authorize execution merely
because the orchestration succeeds against the committed response snapshot.
Binding a real transport or issuing another Crossref request requires a later,
separately defined and explicitly authorized owner action.
