# Editor Core targeted R2 zero-step launcher

The R2 zero-step launcher validates the published R2 commit, dataset and token
closures, the selected R1 checkpoint 8, base model, isolated rootfs, frozen WSL
driver snapshot, CUDA availability, and a distinct empty ext4 output directory.

The launcher contains no training mode and imports no model, optimizer, PEFT,
Transformers, Torch, or bitsandbytes implementation. A successful receipt fixes
the exact physical inputs for a later training route while reporting model load,
optimizer creation, optimizer steps, and training as zero or false.

This remains a development boundary. It performs no adjudication,
certification, promotion, inference, or training.
