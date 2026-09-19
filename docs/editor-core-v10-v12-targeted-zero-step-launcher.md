# Editor Core V10 V1.2 targeted continuation zero-step launcher

`scripts/launch_editor_core_v10_v12_targeted_continuation_zero_step.py` is the
fail-closed validation entry point for the prepared targeted continuation round.
It binds the publication-safe active development state, dataset/config/token
audit closure, physical base model, V10 V1.2 parent adapter and final checkpoint,
isolated runtime rootfs, CUDA driver snapshot, and a distinct empty ext4 output.
The source commit/tree ancestry and the launcher, runtime probe, and driver
manifest helper bytes are included in the validation closure.

The launcher supports zero-step validation only. It has no training mode, does
not import model classes, does not load weights, does not construct an optimizer,
and does not write the output directory. Its receipt is emitted to standard
output and records zero model loads, zero optimizer creation, zero optimizer
steps, and zero training.

The runtime probe executes with isolated network and PID namespaces and the
read-only frozen CUDA snapshot. A later training execution must be separately
authorized and must use a dedicated training worker compatible with the targeted
128-row configuration; the historical V10 trainer is not silently reused because
its frozen 480-row contract is incompatible with this round.
