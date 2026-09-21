# Editor Core targeted R6 zero-step launcher

The launcher requires published dataset commit
`9a164a9d6585836fd9ba83245cb978557896a518` and its exact tree and 14
blob contents. It checks ancestry on the configured upstream branch, the R6
dataset and tokenizer closure, R2 step-9 checkpoint and adapter identities,
the identity-bound development-only R3 rejection, and the byte-exact R4 and R5
semantic rejections. R3, R4, and R5 cannot substitute as training parents.

It also validates the physical base model, isolated rootfs, frozen WSL driver
snapshot, CUDA availability, and an existing, empty, native ext4 output
directory. The successful local smoke used a temporary ext4 fixture directory
and removed it afterward. This receipt does not bind or create a real R6
training output. The published pack contains 18 new and 18 replay training
rows, and a separate 12-case holdout. The launcher checks the pack audit and
the frozen R6 manifest and configuration identities.

Receipt schema version 2 makes this change explicit. `receipt_identity` hashes
the canonical receipt fields that describe stable
source, dataset, parent, runtime-content and zero-training closure. The output
directory's device and inode are reported separately as
`output_runtime_observation`. They are checked before and after each probe,
but are excluded from the reproducible identity because fresh empty fixture
directories have different inodes. A later consuming route must validate its
own output directory; this zero-step receipt does not authorize one.

The launcher has no training mode and imports no model, optimizer, PEFT,
Transformers, Torch, or bitsandbytes implementation. Its receipt reports model
load, optimizer creation, optimizer steps, inference, and training as zero or
false. A later training route must independently bind its real output and run
a fresh pre-training gate.

This is a development boundary. It performs no adjudication, certification,
promotion, inference, or training.
