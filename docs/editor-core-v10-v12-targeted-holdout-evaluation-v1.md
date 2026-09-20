# Editor Core V10 V1.2 targeted holdout evaluation

This development evaluation compares the retained V10 V1.2 parent, targeted
checkpoint 8, and targeted checkpoint 16 on the same 32-case independent
holdout. The inference runner receives only the request corpus. The answer key
is supplied later to the read-only auditor and is never mounted into the model
runtime.

Inference is deterministic and offline: greedy decoding, one beam, seed zero,
an input ceiling of 3,072 tokens, a generation ceiling of 2,048 tokens, and a
6,268-byte decoded-response envelope. The route byte-binds the base model,
each allowed adapter, request corpus, runner, sealed rootfs, and CUDA snapshot.

The audit reports structural protocol closure, exact-target matches, and
mismatches grouped by the eight frozen failure classes. This is experimental
development evidence. It does not perform release certification, adjudication,
promotion, training, or optimizer activity.
