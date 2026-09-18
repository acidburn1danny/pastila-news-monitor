# V15 executable pre-consumption preflight

The V15 preflight is a read-only gate. It cannot create an attempt or run a
candidate. It pins the published V15 checkpoint commit and tree, checks all 14
published files byte-for-byte, and requires the signed V15 authority audit to
reproduce its Ed25519 signature, source and runtime-object closure, V14 terminal
evidence, frozen driver manifest and isolated CUDA result.
It also validates the frozen qualification matrix, loads the Unicode authority,
and verifies that the required Linux namespace capabilities are available.

The output must already be an empty, owner-controlled native ext4 directory
outside all protected inputs. Its device and inode are included in the receipt.
The gate checks emptiness before and after the authority audit. The receipt
records zero V15 candidate executions and zero V15 attempts. It is not an
attempt authorization and is not a substitute for a final preflight immediately
before any separately authorized consumption.

The separate adversarial audit checks that the live published remote ref contains
the pinned checkpoint, runs the
complete gate, and checks the receipt. Neither command invokes the V15 launcher.
