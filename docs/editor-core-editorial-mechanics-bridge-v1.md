# R2-centered Editorial Mechanics Bridge (development research)

This is a data and evaluation design, not a new Core parent or a training authorization. The development parent remains R2 step-9 (`c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02`). R3–R6 remain unselected. Dynamic authority stays in each runtime request; stable source-bound editorial behavior is the learning target.

## Scope and evidence

R2–R6 evidence shows that small targeted rounds have not reliably improved editorial formulation. Exact-copy behavior can be factually safe yet fail a request for a useful editorial rewrite. The historical 50-mechanism comedy curriculum is a taxonomy, not 50 independent trained models or Core training authority. This bridge abstracts only neutral operations applicable to factual reporting. It imports no Voice or comedy records, adapters, sarcasm, punchlines, or style rewards.

The eight operators are fact selection; compression with qualifiers intact; chronological ordering; precise attribution; contrast with both sides supported; transitions without new facts or causal claims; natural Romanian reformulation; and explicit epistemic/procedural status. Humor-specific inversion, misdirection, ridicule, exaggeration, and cadence for comedic effect are excluded. The source request and source spans define permitted facts for every example.

## Corpus and separation

The deterministic builder creates 12 synthetic event families per operator. Six are train, three development, and three independent holdout, with disjoint case IDs and event families. The result is 48 paired training requests, each with a literal-safe control target and a neutral editorial target. Each training target also has a generic-instruction variant with the same source facts and target text. There are 24 development requests and keys; 24 independent holdout requests and keys; and 96 evaluation-only counterexamples. A separate 48-row baseline replay and 48-row protective replay each draw 16 existing accepted training rows from V10, R1, and R2. No frozen evaluation target or R4 adjudication receipt is replayed.

The control and editorial arms share the exact same input. This isolates target design. For example, qualified compression keeps the allegation conditional and the investigation open; an evaluation-only negative converts it to a confirmed violation. Each operator has a concrete negative with a reason code. Copying the authority may pass factual safety but cannot automatically pass the explicit rewrite criterion. Negative texts are evaluator probes and are never assistant training targets.

Development keys and holdout keys are in separate files and must remain outside inference runtime. Development can be used for debugging and arm selection. Holdout must remain untouched until arm rules are frozen. The generated independent holdout uses separate entities/events but shares the generator's broad templates; it measures transfer across source families, not naturalistic production generalization. Any future Core parent change also requires a separate, fresh naturalistic independent evaluation. R2–R6 frozen holdouts remain evaluation-only and may be used only as regression evidence under their original authority.

## Evaluation contract

Score each response on four independent dimensions before comparing arms:

1. **Factual and epistemic safety:** no unsupported entity, number, relation, intent, cause, certainty increase, lost attribution, or premature procedural conclusion. A material regression blocks parent selection.
2. **Editorial rewrite quality:** requested facts selected, qualifiers retained, coherent ordering and compression, supported contrast, and meaningful paraphrase. Safe source copy can fail this dimension.
3. **Romanian quality:** grammatical case/agreement, natural attribution and verb choice, fluent transitions, no bureaucratic or comic register drift.
4. **Regression protection:** compare against R2 on current development cases and frozen historical evaluation evidence; report case-level wins and losses, not only totals.

Use candidate-blinded, source-bound human semantic review of responses. Exact-string match against a single reference is diagnostic only. Inspect the evaluation-only counterexamples to ensure a scoring rule rejects factually unsafe shortcuts and recognizes the distinction between safe copying and requested editorial transformation. A failure in safety cannot be traded for an improvement in rewrite quality.

## Controlled ablations

All trained arms start independently from the same R2 step-9 parent, use the same 48 source situations and 48 replay slots, and have fresh optimizer state. A0 is an untrained R2 baseline. A1/A2 compare literal-safe versus mechanics targets at the R2-like recipe. A3/A4 repeat that target comparison with two epochs. A1/A3 and A2/A4 isolate exposure/recipe strength. A2/A5 isolate the selection of replay examples using the 48-row protective replay while keeping the replay count, target, and recipe constant. A1/A6 and A2/A7 isolate explicit operator instruction: the sources and target text are unchanged, while the request uses a generic factual rewrite instruction. A6/A7 repeat the target-design comparison under that generic instruction. This measures the effect of explicitly naming the editorial operation; it does not by itself isolate every form of mechanics curriculum. Three predeclared seeds (271828, 314159, 161803) give 21 future research runs, pending separate execution authority. R2-like means 1 epoch/12 optimizer steps; stronger means 2 epochs/24 steps; learning rate 3e-6, batch 1, accumulation 8, BF16, constant schedule, no packing, and a 3072-token sequence cap remain fixed. Exact base-model/runtime binding and token audit are required before any execution.

Interpretation: A2>A1 across seeds with safety intact supports editorial target design. A4>A2 while A3>A1 supports stronger exposure. A5>A2 with fewer regressions supports protective replay. If only stronger control improves, the issue may be recipe strength rather than mechanics. If no arm improves beyond R2, revisit corpus diversity/objective rather than repeat a small targeted round. If editorial gains cause factual regressions, reject those arms and revise safety/replay. Do not select a parent from training loss or synthetic holdout alone.

`scripts/build_editor_core_editorial_mechanics_bridge.py` builds the pack. `scripts/audit_editor_core_editorial_mechanics_bridge.py` verifies identities, source/target binding, split separation, replay provenance, frozen-target exclusion, and external lexical similarity. The manifest binds every generated blob. This work creates no model, checkpoint, optimizer state, adjudication receipt, or release decision.
