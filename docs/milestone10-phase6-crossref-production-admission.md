# Milestone 10 Phase 6 — Crossref Production Capture Admission

## Boundary

Phase 6 is an offline-only qualification of controlled admission and integration
of the exact committed Phase 5 production capture. It performs no Crossref or
OpenAlex request, scheduling, downstream publishing, RFC-3161, or Sigstore work.
It accepts only a new output root; callers cannot provide capture bytes, a proof
root, normalization authority, or prior accepted state.

## Frozen input authority

The sole input is the seven-artifact Phase 5 proof committed at
`a5a13dd2d2f4dde5ed5ec8a2df20c05fea6727c5`, closed by proof tip
`04205ccb73542f3360b3811e31c2caef7adec1dc`. Every artifact is read once from
the fixed repository-relative proof root and checked against its frozen SHA-256
before any Phase 6 output root is created. The completion receipt must bind the
frozen request and raw-capture identities, ten records, and
`PRODUCTION_DIRECT_HTTPS`.

## Admission sequence

After complete input validation, the implementation deterministically normalizes
the response, recreates the Phase 3 immutable record, batch, and state types, and
admits the batch only from the canonical empty state. Durable publication order
is:

1. consumed attempt;
2. normalized record set;
3. integration batch;
4. accepted integration state;
5. completion receipt.

Every completed artifact is canonical and atomically published through the
already qualified Phase 4 durability primitives. A second execution against the
same root is rejected before mutation. An interrupted consumed root can only be
completed by the offline recovery entry, which revalidates the fixed proof and
reproduces every expected byte without accepting replacement input. The
accepted state contains the exact
batch identity in `applied_batch_identities`, and every record binds the Phase 5
raw and normalized identities.

## Runtime closure

The Phase 3 immutable integration types and mapping helpers and the Phase 4
canonical/durable filesystem helpers remain source-hash pinned and identity
snapshotted. Rebinding local constants, local helpers, dependency helpers, or
dependency types fails before output mutation. The module imports no transport,
HTTP, TLS, socket, database, scheduling, or publishing capability.

## Deliberate exclusions

Qualification writes only to test roots. It does not designate or publish a
production accepted-state root. Promoting the qualified state or beginning any
later phase requires separate owner authorization.
