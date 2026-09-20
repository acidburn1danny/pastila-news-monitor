# Editor Core V10 V1.2 targeted R2 holdout evaluation

This independent development evaluation compares the retained R1 checkpoint-8
parent with the R2 step-9 adapter on the frozen 18-case R2 holdout. Each of the
three targeted failure classes contributes six cases.

The isolated inference runtime receives only the request corpus. The answer key
is never mounted into that namespace and is supplied only to the later read-only
auditor. Inference is offline and deterministic: greedy decoding, one beam,
seed zero, a 3,072-token input ceiling, a 2,048-token generation ceiling, and a
6,268-byte decoded-response envelope. The route binds the base model, allowed
adapters, request corpus, runner, rootfs, and CUDA driver snapshot.

The audit closes every output file and inference receipt before reporting
structural validity, exact-target matches, and mismatches by frozen failure
class. These are development evaluation results. They do not select a parent,
promote a model, train, run an optimizer, or access R4 adjudication evidence.
