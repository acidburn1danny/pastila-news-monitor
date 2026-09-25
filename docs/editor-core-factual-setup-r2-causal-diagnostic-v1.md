# EDITOR FACTUAL SETUP R2 Causal Learnability & Stability Diagnostic v1

This is a development research design. It cannot select or promote a parent.
R2 step-9 remains the development parent. No historical holdout is used.

The experiment is a matched 2 x 2 factorial. All arms use the same 72 rows,
the same 24-row replay subset, the same 24 development cases, and seeds
161803, 271828, and 314159. The twelve future runs require separate authority.

The target-signal control uses uniform assistant-token loss. The challenger
uses the identical assistant target bytes and output schema, but weights
contract-critical target spans 3:1. The 48 targeted rows form 24 matched
minimal pairs; replay rows retain uniform loss in both signal designs.

The recipe control reproduces Corrective v1: LR 5e-7, one epoch, gradient
accumulation 8, and nine optimizer steps. The higher-plasticity recipe changes
only LR to 1e-6. This estimates a recipe-strength effect without conflating it
with exposure count, row order, optimizer type, or target bytes.

Before and after every future run, the evaluator records full-target and
critical-span teacher-forced NLL. It separately measures train acquisition,
development generalization, deterministic decoded responses, factual and
epistemic safety, replay retention, full adapter delta, and agreement across
seeds. Likelihood is diagnostic and never replaces semantic output review.

Any material factual or epistemic regression, replay regression, identity
drift, contamination, or seed mismatch stops the affected comparison. The
causal decision table is frozen in the protocol artifact before any run.
