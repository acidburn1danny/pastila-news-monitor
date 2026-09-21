# Editor Core targeted R4 zero-step launcher

The R4 zero-step launcher validates the published R4 commit, dataset and token
closure, the semantic development-only selection of the R2 step-9 parent, the
physical checkpoint and base model, isolated rootfs, frozen WSL driver snapshot,
CUDA availability, and a distinct empty ext4 output directory.

The launcher contains no training mode and imports no model, optimizer, PEFT,
Transformers, Torch, or bitsandbytes implementation. A successful receipt binds
the exact physical inputs for a later training route while reporting model load,
optimizer creation, optimizer steps, and training as zero or false.

This remains a development boundary. It performs no adjudication,
certification, promotion, inference, or training.
