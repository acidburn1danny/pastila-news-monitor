# EDITOR Source-Bound Hybrid Runtime Boundary v1

This boundary implements fixture-only runtime separation for `B0_R2_ONE_PASS`, `B1_EXTRACTIVE_BASELINE`, and `B2_HYBRID`.

It is bound to published commit `50c103a5cf7238588789ed3600693ff4ac2ba053`, pack identity `bbad139fde613c1c912cd53992b4c2be047d73180f6a6ae732dc6348461d28f9`, protocol identity `5a5ef79af85a3b58b3c0e2f46be3f9e3dd573d75dae361c6d6df88588f7c1aea`, exact tokenizer SHA-256 `d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135`, and original R2 step-9 adapter identity `c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02`.

## Arm separation

- B0 prepares the source-bound R2 request and performs no fixture inference.
- B1 deterministically emits required ledger quotes and verifies them.
- B2 runs a fixture proposal through the same verifier and extractive fallback boundary.

The nine arm/seed slots require distinct, new, empty output roots in any future execution authority.

## Zero-step

The executable zero-step verifies the published Git tree, pack and protocol identities, manifest hashes, oracle upper-bound limitation, exact tokenizer bytes, R2 adapter identity, all 48 ledger bindings, and nonempty tokenizer mappings for every request and fallback quote. It loads only the tokenizer implementation. It does not import or load a model.

The zero-step receipt is written atomically only after all checks pass.

## Authority limits

The ledger selection remains an oracle-labelled feasibility upper bound. Autonomous ledger construction is not claimed, and a real route requires independent selection curation.

This boundary has no authority for model load, inference, optimizer creation, training, successor construction, parent selection, promotion, or release. The shell route accepts only `--zero-step-only` and exits with code 64 otherwise.
