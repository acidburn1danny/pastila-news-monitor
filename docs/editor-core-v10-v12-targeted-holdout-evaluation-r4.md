# Editor Core V10 V1.2 targeted R4 holdout evaluation

This independent development evaluation compares the selected R2 step-9
development parent with the R4 step-6 adapter on the frozen 12-case R4 holdout.
All twelve cases are independent `EPISTEMIC_CALIBRATION` cases, split evenly
between attribution/denial/finality and preliminary/contested/pending patterns.

The isolated inference runtime receives only the request corpus. The answer key
is never mounted into that namespace and is supplied only to the later read-only
auditor. Inference is offline and deterministic: greedy decoding, one beam,
seed zero, a 3,072-token input ceiling, a 2,048-token generation ceiling, and a
6,268-byte decoded-response envelope. The route binds the base model, allowed
adapters, request corpus, runner, exact published R4 training-route parent,
rootfs, and CUDA driver snapshot. Git trust is limited to each source check.

The audit closes every output file and inference receipt before reporting
structural validity, exact-target matches, and mismatches by frozen failure
class. Its semantic check requires each attribution case to preserve suspicion,
modality, denial, and non-finality, and each preliminary case to preserve the
provisional finding, modality, objection, and unresolved status. Exact textual
matching remains diagnostic because faithful paraphrases are permitted. These
are development evaluation results. They do not select a parent, promote a
model, train, run an optimizer, or access R4 adjudication evidence.
