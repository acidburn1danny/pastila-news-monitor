# VNext SCOUT Production Closure v1

Status: **isolated production-closure candidate; not active**.

## Decision

The existing VNext SCOUT proved that RSS/Atom capture, explicit event selection, and a self-contained SourcePacket are sufficient foundations. It was not production-closed because it owned a private SQLite schema, treated compressed feeds as XML bytes, used single-link title grouping, and coupled runtime preflight to EDITOR/R2 paths.

This closure keeps the demonstrated product responsibilities and rebuilds their boundary around the published Shared Foundation, Canonical Workflow, and Consolidated SQLite State boundaries. It does not migrate legacy SCOUT code or data.

## Production boundary

SCOUT owns HTTPS RSS/Atom/RDF discovery and capture, source provenance, conservative cross-source grouping, explicit user event selection, and SourcePacket construction. It does not rank, summarize, edit, accept facts, generate VOICE, assemble FINAL, or implement GUI behavior.

Transport is bounded to 2 MB compressed and 4 MB decompressed, supports gzip, rejects non-HTTPS redirects and XML DTD/entity declarations, and isolates failures per source. A bounded standard-library pool uses eight workers by default; results are sorted before identity construction, so scheduling cannot change evidence. Feed entry text is labelled `FEED_ENTRY_SOURCE_TEXT`; no claim of full-article capture is made.

## Persistence and recovery

The published SQLite boundary owns schema, writer serialization, WAL, migrations, integrity, backup, and recovery. SCOUT uses its public transaction hook so capture rows commit with `DISCOVERED → CAPTURED`, groups with `CAPTURED → GROUPED`, explicit selection with `GROUPED → SELECTED`, and packet reference with `SELECTED → SOURCE_PACKET_READY`. The canonical workflow remains the only transition authority.

Immutable capture and packet payloads are content addressed under the supplied fixture root. Publishing a payload before its database transaction can only leave an ineligible orphan; it cannot create eligible partial state. Replay uses the published idempotency contract.

## Grouping

Grouping is deterministic, cross-source, and conservative. A merge requires at least three shared title tokens, 60% containment overlap, compatible explicit numbers, and compatible demonstrated named tokens. Complete-link grouping prevents transitive chain merges. Missed merges remain separate selectable events; false merges are treated as the higher-risk error.

## Source-set evidence

A bounded point-in-time diagnostic observed all 54 configured feeds. Initially 53 parsed; all 1,462 sampled entries had title/link and dates, while 1,459 had at least 40 characters of description. The sole failure was The Independent, whose XML response was gzip encoded. Bounded gzip support repaired the cause and a fresh live retest parsed 50 entries. Total observations were 56, below the mandatory 100-observation checkpoint.

This supports RSS/Atom as the primary capture mechanism. It does not prove full article completeness or naturalistic grouping accuracy. Those remain operational monitoring concerns and do not justify a general HTML crawler, model grouping, or article-body dependency in this closure.

## KEEP / SIMPLIFY / REBUILD / DROP

- KEEP: published 54-source configuration, RSS/Atom parsing concept, explicit event selection, self-contained SourcePacket.
- SIMPLIFY: standard-library HTTPS transport, one conservative grouping algorithm, one SourcePacket route.
- REBUILD: persistence interaction on the published SQLite boundary; gzip/limit/security handling; complete-link grouping; atomic workflow receipts.
- DROP: private SCOUT schema, EDITOR/R2 preflight coupling, AI ranking, legacy reconciliation layers, EventAuthorityBundle, EvidencePacket, selector, factual ledger, desktop/GUI bindings, HTML adapter as a mandatory runtime path.

## Limitations

Network health is time varying. Feed descriptions may be excerpts. Naturalistic grouping sensitivity and precision have not been estimated from a labeled production cohort; fixture evidence demonstrates invariants and known failure protection. Production activation should add observation-only source health and grouping review without making them hidden runtime authorities.
