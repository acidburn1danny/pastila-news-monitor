# Editor Core V10 V1.2 targeted R5 holdout evaluation

This independent development evaluation compares the selected R2 step-9
development parent with the R5 step-6 adapter on the frozen 12-case R5 holdout.
All twelve cases are independent `EPISTEMIC_CALIBRATION` cases, split evenly
between attribution/denial/finality and preliminary/contested/pending patterns.

The isolated inference runtime receives only the request corpus. The answer key
is never mounted into that namespace and is supplied only to the later read-only
auditor. Inference is offline and deterministic: greedy decoding, one beam,
seed zero, a 3,072-token input ceiling, a 2,048-token generation ceiling, and a
6,268-byte decoded-response envelope. The route binds the base model, allowed
adapters, request corpus, runner, exact published R5 training-route parent,
rootfs, and CUDA driver snapshot. Git trust is limited to each source check.

The audit closes every output file and inference receipt before reporting
structural validity, exact-target matches, and mismatches by frozen failure
class. Its semantic check requires each attribution case to preserve suspicion,
modality, denial, and non-finality, and each preliminary case to preserve the
provisional finding, modality, objection, and unresolved status. Exact textual
matching remains diagnostic because faithful paraphrases are permitted. These
are development evaluation results. They do not select a parent, promote a
model, train, run an optimizer, or access R5 adjudication evidence.

## Local evaluation result (2026-09-21)

Both isolated inference runs completed all 12 cases with valid JSON, terminal
EOS, and no output-byte overflow. The read-only auditor found 10 byte-identical
responses. Cases `ec-v10-v12-r5-h-13` and `ec-v10-v12-r5-h-15` changed only in
the first sentence: R5 used less grammatical attribution wording. A manual
case-by-case comparison against the frozen authority spans found no new
semantic pass, no changed factual claim binding, and no epistemic regression.
The remaining development issues are attribution phrasing and grammatical
quality, not a missing schema or source binding. The lexical semantic check is
diagnostic; it cannot by itself decide parent selection. R2 step-9 remains the
development parent because the independent holdout shows no R5 improvement.
