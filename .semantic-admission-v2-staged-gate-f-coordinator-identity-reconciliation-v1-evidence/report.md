# Staged Gate F coordinator identity reconciliation V1

The historical coordinator manifest is preserved byte-for-byte with canonical identity `9d2f55be9771f0da0ab6a547217e8fc450167d30651bd12d7898fd36830a47bc`. It expects coordinator source SHA-256 `0ee8279f8ad7ecc2b372538597f47cd6084786cce1dba143e08e841b97558c5a`.

That expected source byte sequence is absent from every reachable Git version of the coordinator path and from current repository content. It was not reconstructed or fabricated. The other four artifacts recorded by the historical manifest still match their recorded SHA-256 values.

The current coordinator source was introduced at commit `b449a8667f9e956eb74cecc1f91c6ac8d8149c0c`, Git blob `136ebb1ed3ad9b25ea304bcee0fcf34484a7d4a1`, and has SHA-256 `339ec6a6c5eddc26836f58cf19478df4cb7bc7bf8beb5e3cf8a159881ae3d82e`. This superseding receipt binds that reproducible current source without altering or silently rebinding the historical manifest.

No byte-equivalence or semantic-equivalence claim is made between the unavailable historical source and the current canonical-identity-normalized source. This is identity reconciliation only. It grants no provider, model, Stage C, runner, probe, inference, runtime, or production authority.
