# Editor Core V10 V1.2 targeted R5 training route

The dedicated R5 worker consumes exactly the published 36-row corpus: 12
targeted examples and 24 replay anchors. The independent 12-case holdout and
adjudication evidence are excluded from training. R3 and R4 adapters remain
rejected as development parents.

The frozen plan continues the selected R2 checkpoint 9 for one epoch with seed
314159, micro-batch 1, gradient accumulation 6, a new paged AdamW 8-bit
optimizer at `5e-7`, a constant schedule without warmup, BF16, no packing, six
optimizer steps, and a final checkpoint at step 6.

The future executable route binds the published zero-step correction commit and tree,
and byte-binds the R5 worker, published R5 zero-step
launcher, corpus, configuration, parent checkpoint receipt and adapter, base model, rootfs, and frozen
CUDA snapshot. It requires an explicit owner execution gate, native empty ext4
output, a fresh zero-step gate immediately before namespace entry, read-only inputs, and isolated network, PID, mount, IPC, and UTS
namespaces. The R2 worker and R1 parent cannot substitute.

Publication checks trust only the exact repository path for each Git command.
The route does not modify the invoking user's persistent Git configuration.

The fixture smoke imports no ML runtime and performs no model load, optimizer
construction, backward pass, checkpoint write, or optimizer step. Construction
and audit of this route do not authorize real training.
