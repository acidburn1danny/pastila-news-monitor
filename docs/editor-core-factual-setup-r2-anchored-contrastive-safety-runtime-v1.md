# EDITOR R2 Anchored Contrastive Safety Diagnostic v1 — runtime boundary

This boundary binds the four-arm, three-seed diagnostic to published source
commit `eadbddf23da3408f8cfb8233823f4f8fd974519f`, R2 step-9, the exact
tokenizer, frozen rootfs, frozen S0 recipe, and frozen evaluator. The executable
launcher enters a fresh mount/network namespace and runs the tokenizer-only
preflight from the frozen rootfs without inheriting host Python packages.

The current revision authorizes fixture execution and tokenizer-only zero-step
only. It does not authorize model loading, optimizer creation, training,
inference, parent selection, promotion, or release. Weighted-SFT T1/S0 remains
closed and reference-only. Every slot requires a distinct empty output root;
terminal evidence is written atomically and last.

The preflight validates 48 chosen/rejected minimal pairs, 24 R2 retention
anchors, exact bytes, token mappings, three matched row orders, and all twelve
arm/seed slots. Historical holdouts, VOICE, and CHIEF EDITOR are outside this
boundary.
