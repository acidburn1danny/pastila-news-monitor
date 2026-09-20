# Editor Core V10 V1.2 targeted R3 training route

The dedicated R3 worker consumes exactly the published 48-row corpus: 36
targeted failure-mining examples and 24 replay anchors. The independent 12-case
holdout, R4 evidence, and adjudication evidence are excluded from training.

The frozen plan continues the selected R2 checkpoint 9 for one epoch with seed
271828, micro-batch 1, gradient accumulation 8, a new paged AdamW 8-bit
optimizer at `3e-6`, a constant schedule without warmup, BF16, no packing, six
optimizer steps, and a final checkpoint at step 6.

The future executable route binds the published zero-step commit and tree,
and byte-binds the R3 worker, published R3 zero-step
launcher, corpus, configuration, parent checkpoint receipt and adapter, base model, rootfs, and frozen
CUDA snapshot. It requires an explicit owner execution gate, native empty ext4
output, read-only inputs, and isolated network, PID, mount, IPC, and UTS
namespaces. The R2 worker and R1 parent cannot substitute.

The fixture smoke imports no ML runtime and performs no model load, optimizer
construction, backward pass, checkpoint write, or optimizer step. Construction
and audit of this route do not authorize real training.
