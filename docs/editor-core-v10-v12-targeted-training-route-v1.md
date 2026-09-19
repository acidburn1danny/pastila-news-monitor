# Editor Core V10 V1.2 targeted training route

The dedicated worker consumes exactly the published 128-row targeted corpus:
64 new examples followed by 64 replay anchors. It preserves the separate
32-case holdout and rejects any configuration that enables holdout, R4, or human
receipt use for training.

The frozen plan is one epoch, deterministic shuffle seed 314159, micro-batch 1,
gradient accumulation 8, a new paged AdamW 8-bit optimizer at `5e-6`, constant
schedule without warmup, BF16, no packing, 16 optimizer steps, and checkpoints
at optimizer steps 8 and 16.

The worker disables PyTorch's experimental `_native` `bmm` override before
model execution. This preserves the established V10/V12/V14 runtime behavior
and uses the packaged CUDA kernel without requiring an unbound runtime C
compiler inside the sealed rootfs.

`scripts/run_editor_core_v10_v12_targeted_continuation_v1.sh` is the future
execution route. It requires an explicit execution arming flag and owner-side
environment gate, verifies every physical input identity, uses read-only input
mounts, an isolated network/PID/mount namespace, the frozen CUDA snapshot, and a
distinct empty ext4 output. It was not invoked during construction.

`scripts/smoke_editor_core_v10_v12_targeted_training_route_v1.py` exercises only
the deterministic fixture plan and static route closure. ML libraries remain
inside the execution-only function and the smoke performs no model load,
optimizer construction, backward pass, or optimizer step.
