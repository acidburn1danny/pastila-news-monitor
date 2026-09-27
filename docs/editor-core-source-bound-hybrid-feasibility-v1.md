# EDITOR Source-Bound Hybrid Feasibility Diagnostic v1

## Verdict

`PASS + 0 BLOCKERS` for design, diagnostic-pack, and fixture-only executable-boundary closure.

The diagnostic has no real execution authority. No model was loaded, no inference was run, no optimizer was created, and no training was performed. R2 step-9 remains the baseline and development parent.

## Objective

The diagnostic tests whether factual authority can be moved from probabilistic model behavior into a source-bound ledger. The textual realizer may select order and connective language, but it cannot create factual authority. Its output is accepted only after deterministic verification; otherwise it is discarded and replaced with a source-extractive fallback.

## Ledger authority model

Authority order:

1. source spans are the sole primary factual authority;
2. ledger atoms are byte-bound derivations from one source span each;
3. required obligations identify what the setup must preserve;
4. the realizer is non-authoritative;
5. the verifier decides acceptance;
6. the fallback emits ordered quotes from required atoms.

The pack contains 48 ledgers: 24 development and 24 replay-retention cases, with 144 source-bound atoms and 192 required obligations. Existing historical holdouts are not used.

Each atom records its type, source/span identity, source SHA-256, exact quote, UTF-8 byte offsets, selection status, actors/entities, numbers, epistemic markers, and procedural markers. Every quote reproduces the indicated source byte slice.

## Reconciliation

The reconciliation contract freezes:

- deterministic token and number extraction;
- exact-overlap plus lexical-similarity obligation binding;
- fail-closed handling of unbound requirements;
- exact number surfaces and roles;
- source-only actor/entity authority;
- preservation of epistemic and procedural markers;
- separate representation of competing claims without automatic resolution;
- explicit `REQUIRED`, `OPTIONAL`, and `EXCLUDED` selection states.

Oracle targets are used only to label fixture selection for this feasibility diagnostic. A future real acquisition route must obtain that curation independently; this pack does not claim autonomous ledger construction.

## Text realization and verifier

The realizer proposes two or three sentence objects, each with text and nonempty ledger-atom bindings. The verifier rejects proposals with:

- wrong case identity or sentence count;
- missing required or included excluded atoms;
- unauthorized words, actors, numbers, or bindings;
- missing numbers, epistemic markers, or procedural status;
- repetitive clauses;
- malformed sentence bindings.

Rejected text is never authoritative evidence. The boundary validates a deterministic fallback consisting of two or three ordered required-atom quotes. If that fallback cannot preserve all obligations within the sentence budget, the case fails closed.

## Predeclared comparison

- `B0_R2_ONE_PASS`: existing R2 source-to-setup behavior.
- `B1_EXTRACTIVE_BASELINE`: deterministic required-atom quotes.
- `B2_HYBRID`: separate textual realization followed by ledger verification and fallback.

All arms keep cases, partitions, seeds, ledger, metrics, and the two-to-three sentence contract fixed. Later semantic scoring must measure factual safety, coverage, number roles, epistemic and procedural retention, repetition, fallback rate, fallback sufficiency, and functional Romanian.

## Terminal rules

`STOP` has precedence over `REVISE`, which has precedence over `CONTINUE`.

### STOP

- any required fact cannot be source-bound;
- any accepted novel actor, number, or epistemic/procedural upgrade;
- hybrid has no safety or sufficiency advantage over R2;
- fallback cannot preserve requirements within three sentences.

### REVISE

- ledger is valid but fallback exceeds 25%;
- extractive output is safe but not functional Romanian;
- hybrid is safe but does not improve over extractive realization;
- direction is not stable in at least two of three seeds.

### CONTINUE

- all admitted ledgers are valid;
- accepted outputs have zero factual or epistemic drift;
- hybrid improves sufficiency over R2 without replay regression;
- hybrid improves functional Romanian over extractive output;
- the direction replicates in at least two of three seeds;
- the remaining trainable residual is isolated to realization rather than fact selection.

Continuation remains development research and cannot select a parent.

## Fixture closure

- 48/48 ledgers validated;
- 48/48 extractive proposals accepted;
- 150 adversarial proposals rejected and safely routed to fallback;
- 192 additional adversarial checks passed;
- zero model load, inference, optimizer, training, holdout access, parent selection, promotion, or release.

## Next action

Create a checkpoint commit limited to the protocol/pack, builder, fixture boundary, adversarial auditor, report, and dedicated test. Then run byte-exact rebuild, dedicated tests, fixture smoke, and a fresh adversarial audit. Stop before publication and before any real-runtime boundary.
