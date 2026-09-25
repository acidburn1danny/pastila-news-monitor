# EDITOR FACTUAL SETUP R2 T1/S0 Replay-Protected Diagnostic v1

## Purpose

This development-research successor tests one causal change: whether explicit replay weighting can preserve the useful T1/S0 learning signal while preventing the procedural, numeric, actor-fidelity, and repetition regressions observed in the terminal factorial diagnostic.

## Controlled contrast

Both arms use R2 step-9, recipe S0 (`5e-7`), seeds `161803`, `271828`, and `314159`, identical 72 training rows, identical assistant target bytes, matched row ordering, the frozen evaluator, and frozen deterministic decoding.

- `T1_S0_EXISTING_CONTROL` uses the published T1 signal unchanged.
- `T1_S0_REPLAY_PROTECTED` keeps all 48 corrective signal rows byte-identical and adds critical-span weighting only to the editorial `text` value of all 24 replay rows.

The complete safe two-to-three-sentence replay target is weighted. This simultaneously protects the required actor, numbers, qualifications, and procedural closure while teaching the complete non-repetitive sequence. JSON scaffolding, case identifiers, metadata, and claim bindings are never critical spans.

The repetition detector and all semantic scoring rules apply identically to both arms. They are measurement gates, not arm-specific training changes.

## Authority and limits

This pack authorizes no model load, optimizer creation, training, parent selection, promotion, or release. It does not access historical holdouts and contains no VOICE or CHIEF EDITOR objective. A later real experiment requires a separately published execution boundary and explicit owner authorization.

## Decision rule

- `STOP`: any material factual, epistemic, or replay regression, or no replicated development signal.
- `REVISE`: replay retention improves but the targeted development signal disappears.
- `CONTINUE_RESEARCH`: the protected arm preserves the T1/S0 development signal and has zero material replay regressions in at least two of three seeds.

Even `CONTINUE_RESEARCH` has no development-parent selection authority.
