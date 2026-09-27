# EDITOR VNext Minimal Source Authority Diagnostic v1

## Verdict

`PASS + 0 BLOCKERS` for design, self-contained diagnostic pack, and fixture-only boundary. No model was loaded and no inference, optimization, training, holdout access, parent selection, promotion, release, cleanup, or legacy deletion occurred.

## Minimal architecture

The active design contains three contracts only: `SourcePacket`, `EvidencePacket`, and `EditorSetup`.

`SourcePacket` owns immutable source bytes and provenance. `EvidencePacket` selects existing span IDs and carries deterministic critical literals and unresolved flags; it cannot contain new factual prose. `EditorSetup` is R2 output with internal sentence-to-span citations and a verifier result. VOICE remains the separate creative stage.

## Diagnostic arms

1. `V0_FULL_SOURCE`: all source spans are available to the frozen R2 reference realizer.
2. `V1_DETERMINISTIC_EVIDENCE`: the canonical first span plus spans containing explicit critical literals.
3. `V2_DETERMINISTIC_PLUS_BOUNDED_SELECTOR`: V1 plus an ID-only selector that may add existing spans or abstain.
4. `ORACLE_UPPER_BOUND`: measurement only.

The fixture selector uses oracle-required span IDs only as an upper-bound proxy. It makes no claim of autonomous selection. Real inference remains unauthorized.

## Dependency closure

The bundle embeds all 48 cases and all source bytes used by fixture execution. The boundary reads only the VNext bundle and manifest; it has no runtime dependency on legacy ledgers, WSL roots, SSDs, or backups. The manifest explicitly names the R2 adapter, checkpoint, and tokenizer identities that a future real-runtime preflight must materialize and verify before model load.

Only three diagnostic outputs are intended to persist: bundle, dependency manifest, and this report. Generations, caches, intermediate packets, rejected outputs, and per-case debug traces are ephemeral by default.

## Claim limits

Fixture closure proves byte identity, arm isolation, selector confinement, and dependency declaration. It does not prove semantic selector quality, final setup quality, naturalistic transfer, or production readiness.
